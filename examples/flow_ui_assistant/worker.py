"""Bridge one existing assistant provider job to a browser operator.

Run from the same machine as the FlowKit server. This example never enqueues
jobs, changes scenes, or sends requests to Google. See README.md for the
browser half and the explicit handoff between steps.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from uuid import UUID, uuid4


def browser_job(job: dict, config: dict) -> dict:
    """Translate the batch producer's payload into one browser operation."""
    extra = job.get("extra") or {}
    if job.get("provider") != "assistant" or job.get("kind") != "video":
        raise ValueError("Expected an assistant i2v job")
    if extra.get("model_family") != "omni_flash" or not job.get("start_url") or not job.get("end_url"):
        raise ValueError("This example needs Omni and both scene frame URLs")
    project = str(UUID(config["project_id"]))
    if project != extra.get("project_id"):
        raise ValueError("Flow project does not match the job")
    try:
        start, end = (config["assets"][str(UUID(extra[f"{key}_media_id"]))] for key in ("start", "end"))
    except (KeyError, ValueError, AttributeError) as exc:
        raise ValueError("Both job frame IDs need a mapping to existing Flow assets") from exc
    duration = extra.get("duration_s")
    aspect = {"VERTICAL": "9:16", "HORIZONTAL": "16:9"}.get(job.get("orientation"))
    resolution = config["resolution"]
    model = config["model"]
    cap = config["max_credits"]
    prompt = job.get("prompt", "").strip()
    if (duration not in (4, 6, 8, 10) or not aspect or resolution not in ("360p", "720p")
            or not isinstance(model, str) or not model.startswith("Omni ") or type(cap) is not int or cap < 0
            or not prompt or not all(isinstance(name, str) and name.strip() for name in (start, end))):
        raise ValueError("Unsupported Omni settings or empty prompt/asset name")
    return {"id": job["id"], "prompt": prompt, "extra": {
        "project_url": f"https://flow.google.com/project/{project}",
        "start_asset": start, "end_asset": end, "aspect": aspect,
        "duration": int(duration), "resolution": resolution, "model": model, "max_credits": cap,
    }}


def queue_call(api: str, path: str, body: dict | None = None) -> dict:
    url = urlsplit(api)
    if (url.scheme != "http" or url.hostname not in ("localhost", "127.0.0.1", "::1")
            or url.username or url.password or url.path.rstrip("/") != "/api" or url.query or url.fragment):
        raise ValueError("Use a local FlowKit API base such as http://127.0.0.1:8100/api")
    request = Request(api.rstrip("/") + "/provider-jobs/" + path,
                      data=None if body is None else json.dumps(body).encode(),
                      headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=10) as response:
        return json.load(response)


def stage_mp4(source: Path, output: Path, settings: dict) -> str:
    """Validate the downloaded file before reporting a result to FlowKit."""
    if source.suffix.lower() != ".mp4" or not source.is_file():
        raise ValueError("Expected a downloaded MP4")
    probe = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration",
        "-of", "json", str(source),
    ], timeout=30))
    short = int(settings["resolution"][:-1])
    long = round(short * 16 / 9)
    expected = (short, long) if settings["aspect"] == "9:16" else (long, short)
    video = [(s.get("width"), s.get("height")) for s in probe["streams"] if s["codec_type"] == "video"]
    if video != [expected] or abs(float(probe["format"]["duration"]) - settings["duration"]) > 0.25:
        raise ValueError("Downloaded video does not match the job's size or duration")
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-xerror", "-i", str(source),
                    "-map", "0:v", "-map", "0:a?", "-f", "null", "-"], check=True, timeout=120)

    def sha256(path: Path) -> bytes:
        digest = hashlib.sha256()
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.digest()

    if not output.exists():
        with source.open("rb") as src, output.open("xb") as dst:
            shutil.copyfileobj(src, dst)
    if sha256(source) != sha256(output):
        raise ValueError("Existing staged file differs; no result was sent")
    return output.resolve().as_uri()


def run(args: argparse.Namespace) -> dict:
    job_id = args.job_id
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", job_id):
        raise ValueError("Invalid provider job ID")
    job = queue_call(args.api, job_id)
    lease_path = args.state_dir / f"{job_id}.json"
    intent_path = args.state_dir / f"{job_id}.submit-intent"

    if args.action == "claim":
        if lease_path.exists() or intent_path.exists() or job["status"] != "QUEUED" or job["retry_count"] != 0:
            raise ValueError("Job was already handled; reconcile in Flow before submitting again")
        config = json.loads(args.config.read_text(encoding="utf-8-sig"))
        prepared = browser_job(job, config)
        args.state_dir.mkdir(parents=True, exist_ok=True)
        worker_id = f"flow-ui-example-{uuid4().hex}"
        claimed = queue_call(args.api, f"{job_id}/claim", {"worker_id": worker_id, "lease_ttl_s": 300})
        if claimed["retry_count"] != 1 or claimed["claimed_by"] != worker_id:
            raise ValueError("Expected a fresh, owned lease")
        with lease_path.open("x", encoding="utf-8") as lease:
            json.dump({"worker_id": worker_id, "job": prepared}, lease, ensure_ascii=False)
        return prepared

    lease = json.loads(lease_path.read_text(encoding="utf-8"))
    owner = {"worker_id": lease["worker_id"]}
    if job.get("claimed_by") != owner["worker_id"] or job.get("retry_count") != 1:
        raise ValueError("Job lease is no longer owned; reconcile in Flow")
    if args.action == "complete" and job["status"] == "SUCCEEDED":
        return job  # Recover a lost local /complete response without downloading again.
    if job["status"] not in ("CLAIMED", "RUNNING"):
        raise ValueError("Job is no longer live; reconcile in Flow")
    if args.action == "heartbeat":
        return queue_call(args.api, f"{job_id}/heartbeat", {**owner, "lease_ttl_s": 300})
    if args.action == "fail":
        return queue_call(args.api, f"{job_id}/fail", {**owner, "error": args.reason})
    if args.action == "mark-submit":
        if job["progress"] != 0:
            raise ValueError("Submit intent already recorded")
        with intent_path.open("x", encoding="utf-8") as intent:
            intent.write("Do not submit again. Inspect the existing Flow result.\n")
        return queue_call(args.api, f"{job_id}/progress", {
            **owner, "progress": 1, "message": "Flow UI submit intent; reconcile before another click",
        })
    if not intent_path.is_file() or job["progress"] < 1:
        raise ValueError("Expected a recorded submit intent")
    output_url = stage_mp4(args.video, args.state_dir / f"{job_id}.mp4", lease["job"]["extra"])
    return queue_call(args.api, f"{job_id}/complete", {**owner, "result": {"output_url": output_url}})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://127.0.0.1:8100/api")
    parser.add_argument("--state-dir", type=Path, required=True)
    commands = parser.add_subparsers(dest="action", required=True)
    for action in ("claim", "mark-submit", "heartbeat", "complete", "fail"):
        command = commands.add_parser(action)
        command.add_argument("job_id")
        if action == "claim":
            command.add_argument("--config", type=Path, required=True)
        if action == "complete":
            command.add_argument("--video", type=Path, required=True)
        if action == "fail":
            command.add_argument("--reason", required=True)
    try:
        # ASCII JSON keeps captured output portable across terminal encodings.
        print(json.dumps(run(parser.parse_args())))
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print(f"Flow UI worker stopped: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

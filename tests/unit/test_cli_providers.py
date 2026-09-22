"""Unit tests for CLI provider backends (agent/services/video_reviewer.py)
and the provider-switch API (agent/api/providers.py).

Heavy mocking of asyncio.create_subprocess_exec — no real subprocesses,
no real filesystem writes to agent/providers.json.
"""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from agent.services.video_reviewer import (
    _run_claude_cli,
    _run_agy_cli,
    _run_codex_cli,
    _analyze_cli,
    _build_prompt,
    _frame_filter,
    _parse_agy_envelope,
)
from agent.services import cli_providers
from agent.api import providers as providers_api


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_proc(stdout=b"", stderr=b"", returncode=0):
    """Build a MagicMock standing in for an asyncio subprocess handle."""
    proc = MagicMock()
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    proc.returncode = returncode
    proc.kill = MagicMock()
    return proc


# ---------------------------------------------------------------------------
# _run_claude_cli
# ---------------------------------------------------------------------------

class TestRunClaudeCli:
    @pytest.mark.asyncio
    async def test_model_effort_and_add_dirs_reach_the_argv(self):
        """The default provider's new arguments. agy had three tests for this
        and claude had none, which is backwards — claude is what runs unless
        someone changes the setting."""
        proc = make_proc(stdout=b"ok", returncode=0)
        with patch(
            "agent.services.video_reviewer.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=proc),
        ) as mock_exec:
            await _run_claude_cli(
                "hello", model="sonnet", effort="high", add_dirs=("/tmp/sheets",))
        argv = mock_exec.call_args[0]
        assert argv[argv.index("--model") + 1] == "sonnet"
        assert argv[argv.index("--effort") + 1] == "high"
        assert argv[argv.index("--add-dir") + 1] == "/tmp/sheets"
        # Unlike agy, claude's model does not encode the effort, so both stay.
        assert "--effort" in argv and "--model" in argv

    @pytest.mark.asyncio
    async def test_a_failure_carries_both_streams(self):
        """claude puts the readable sentence on stdout and buries the machine
        tag under paragraphs of unrelated context advice on stderr. Dropping
        stdout left the operator reading about token windows."""
        proc = make_proc(
            stdout=b"There's an issue with the selected model (nope-xyz).",
            stderr=b"[claude-code:unrecognized_model] {\"model\":\"nope-xyz\"}",
            returncode=1,
        )
        with patch(
            "agent.services.video_reviewer.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=proc),
        ):
            with pytest.raises(RuntimeError) as excinfo:
                await _run_claude_cli("hello", model="nope-xyz")
        message = str(excinfo.value)
        assert "unrecognized_model" in message      # stderr tail
        assert "issue with the selected model" in message  # stdout, previously dropped

    @pytest.mark.asyncio
    async def test_argv_and_return_value(self):
        proc = make_proc(stdout=b'{"ok": true}', stderr=b"", returncode=0)
        with patch(
            "agent.services.video_reviewer.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=proc),
        ) as mock_exec:
            result = await _run_claude_cli("hello")

        args, kwargs = mock_exec.call_args
        assert args == ("claude", "-p", "hello", "--allowedTools", "Read", "--output-format", "text")
        assert result == '{"ok": true}'


# ---------------------------------------------------------------------------
# _run_agy_cli
# ---------------------------------------------------------------------------

def agy_envelope(response: str, **extra) -> bytes:
    """A realistic `agy --output-format json` envelope."""
    env = {
        "conversation_id": "c-1",
        "status": "SUCCESS",
        "response": response,
        "duration_seconds": 1.0,
        "num_turns": 1,
        "usage": {"total_tokens": 10},
    }
    env.update(extra)
    return json.dumps(env).encode()


class TestRunAgyCli:
    @pytest.mark.asyncio
    async def test_argv_asks_for_json_and_unwraps_the_envelope(self):
        proc = make_proc(stdout=agy_envelope('{"ok": true}'), returncode=0)
        with patch(
            "agent.services.video_reviewer.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=proc),
        ) as mock_exec:
            result = await _run_agy_cli("hello")

        args, kwargs = mock_exec.call_args
        assert args[:6] == ("agy", "-p", "hello", "--output-format", "json", "--print-timeout")
        # The answer is the envelope's `response`, not the raw stdout.
        assert result == '{"ok": true}'

    @pytest.mark.asyncio
    async def test_never_passes_the_skip_permissions_flag(self):
        """--dangerously-skip-permissions auto-approves *every* tool, shell
        commands included, for a job whose only need is reading a few JPEGs.
        Steering agy at its file-reading tool achieves the read unprivileged
        (verified against agy 1.2.7), so the flag must never come back."""
        proc = make_proc(stdout=agy_envelope("x"), returncode=0)
        with patch(
            "agent.services.video_reviewer.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=proc),
        ) as mock_exec:
            await _run_agy_cli("hello")
        assert "--dangerously-skip-permissions" not in mock_exec.call_args[0]

    @staticmethod
    async def _argv_for(**kwargs):
        proc = make_proc(stdout=agy_envelope("x"), returncode=0)
        with patch(
            "agent.services.video_reviewer.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=proc),
        ) as mock_exec:
            await _run_agy_cli("hello", **kwargs)
        return mock_exec.call_args[0]

    @pytest.mark.asyncio
    async def test_model_and_add_dirs_reach_the_argv(self):
        argv = await self._argv_for(model="gemini-3.8-flash-low", add_dirs=("/tmp/sheets",))
        assert argv[argv.index("--model") + 1] == "gemini-3.8-flash-low"
        assert argv[argv.index("--add-dir") + 1] == "/tmp/sheets"

    @pytest.mark.asyncio
    async def test_effort_alone_reaches_the_argv(self):
        argv = await self._argv_for(effort="high")
        assert argv[argv.index("--effort") + 1] == "high"
        assert "--model" not in argv

    @pytest.mark.asyncio
    async def test_effort_is_dropped_when_a_model_is_set(self):
        """agy slugs carry the effort — gemini-3.8-flash-low. Verified against
        agy 1.2.7: a mismatched pair is rejected outright ("--model
        gpt-oss-120b-medium conflicts with --effort=low") and a slug with no
        effort in its name refuses --effort at all. The API will not store both,
        but providers.json is hand-editable, so the runner defends too."""
        argv = await self._argv_for(model="gemini-3.8-flash-low", effort="high")
        assert argv[argv.index("--model") + 1] == "gemini-3.8-flash-low"
        assert "--effort" not in argv


class TestParseAgyEnvelope:
    def test_returns_the_response_field(self):
        assert _parse_agy_envelope(agy_envelope("  hi  ").decode()) == "hi"

    def test_denied_tool_with_empty_response_is_an_error_not_an_empty_answer(self):
        """The exact shape of the bug this rewrite fixes: agy auto-denies a
        tool it cannot prompt for, returns an empty response, and still reports
        status SUCCESS on a zero exit code. Read naively that is a silent
        empty review; it has to be an error, and it has to name the tool."""
        raw = agy_envelope(
            "", denied_actions=[{"action": "command", "display_name": "RunCommand"}]
        ).decode()
        with pytest.raises(RuntimeError) as excinfo:
            _parse_agy_envelope(raw)
        assert "RunCommand" in str(excinfo.value)

    def test_a_denied_tool_with_a_confident_answer_is_also_an_error(self):
        """The more dangerous half. The prompt carries the full scoring rubric,
        the scene's image prompt, its video prompt and the character names — so
        agy can write a complete, plausible review from the text alone without
        ever having looked at a frame. A denial means the "use your file-reading
        tool, run no shell command" steering did not hold, so the answer cannot
        be attributed to the images no matter how well-formed it is."""
        raw = agy_envelope(
            '{"dimensions": {"character_consistency": 9.0}, "errors": []}',
            denied_actions=[{"action": "command", "display_name": "RunCommand"}],
        ).decode()
        with pytest.raises(RuntimeError, match="auto-denied"):
            _parse_agy_envelope(raw)

    def test_a_clean_success_carries_no_denials_and_passes(self):
        """The happy path must stay clean — live agy 1.2.7 runs that succeed
        omit denied_actions entirely, so widening the guard costs nothing."""
        assert _parse_agy_envelope(agy_envelope("the answer").decode()) == "the answer"

    def test_bare_prose_on_a_zero_exit_code_is_an_error(self):
        """What agy actually prints when the permission is denied and no
        --output-format json is honoured. rc is 0, so _spawn_and_check lets it
        through and this is the only place left to catch it."""
        with pytest.raises(RuntimeError, match="non-JSON"):
            _parse_agy_envelope(
                "jetski: no output produced — a tool required the \"command\" permission"
            )

    def test_empty_stdout_is_an_error(self):
        with pytest.raises(RuntimeError, match="no output"):
            _parse_agy_envelope("   ")

    def test_empty_response_is_an_error(self):
        with pytest.raises(RuntimeError, match="empty response"):
            _parse_agy_envelope(agy_envelope("").decode())

    def test_non_success_status_is_an_error(self):
        with pytest.raises(RuntimeError, match="status"):
            _parse_agy_envelope(agy_envelope("hi", status="ERROR").decode())


# ---------------------------------------------------------------------------
# _run_codex_cli
# ---------------------------------------------------------------------------

def fake_codex_exec(captured, answer: str = "codex analysis result", returncode: int = 0):
    """Stand in for the codex binary: record argv, write the -o file, exit."""
    async def _run(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        out_path = Path(args[args.index("-o") + 1])
        out_path.write_text(answer)
        return make_proc(stdout=b"", stderr=b"", returncode=returncode)
    return _run


class TestRunCodexCli:
    @pytest.mark.asyncio
    async def test_argv_structure_and_output_file_roundtrip(self):
        contact_sheets = [Path("/tmp/sheet_00.jpg"), Path("/tmp/sheet_01.jpg")]
        captured = {}

        with patch(
            "agent.services.video_reviewer.asyncio.create_subprocess_exec",
            new=AsyncMock(side_effect=fake_codex_exec(captured)),
        ):
            result = await _run_codex_cli("analyze this", contact_sheets)

        args = captured["args"]
        out_path = Path(args[args.index("-o") + 1])
        assert args == (
            "codex", "exec", "--skip-git-repo-check", "--sandbox", "read-only",
            "-i", str(contact_sheets[0]),
            "-i", str(contact_sheets[1]),
            "-o", str(out_path),
            "analyze this",
        )

        assert result == "codex analysis result"
        # finally: out_path.unlink(missing_ok=True) must have run
        assert not out_path.exists()

    @pytest.mark.asyncio
    async def test_never_bypasses_the_sandbox(self):
        """-i hands codex the image bytes directly, so the run needs neither a
        shell nor a writable filesystem. read-only already implies
        approval:never, so nothing hangs — the bypass flag bought nothing and
        cost the sandbox."""
        captured = {}
        with patch(
            "agent.services.video_reviewer.asyncio.create_subprocess_exec",
            new=AsyncMock(side_effect=fake_codex_exec(captured)),
        ):
            await _run_codex_cli("analyze this", [Path("/tmp/sheet_00.jpg")])
        assert "--dangerously-bypass-approvals-and-sandbox" not in captured["args"]
        assert "--sandbox" in captured["args"]

    @pytest.mark.asyncio
    async def test_model_and_effort_reach_the_argv(self):
        captured = {}
        with patch(
            "agent.services.video_reviewer.asyncio.create_subprocess_exec",
            new=AsyncMock(side_effect=fake_codex_exec(captured)),
        ):
            await _run_codex_cli(
                "analyze this", [Path("/tmp/s.jpg")], model="gpt-5.6-sol", effort="high"
            )
        argv = captured["args"]
        assert argv[argv.index("-m") + 1] == "gpt-5.6-sol"
        # codex has no --effort; the reasoning level is a TOML config override.
        assert argv[argv.index("-c") + 1] == 'model_reasoning_effort="high"'

    @pytest.mark.asyncio
    async def test_empty_output_file_is_an_error_not_an_empty_answer(self):
        """codex can exit 0 having written nothing. Returning "" from here
        surfaces as a JSON decode error three frames away from the cause."""
        captured = {}
        with patch(
            "agent.services.video_reviewer.asyncio.create_subprocess_exec",
            new=AsyncMock(side_effect=fake_codex_exec(captured, answer="")),
        ):
            with pytest.raises(RuntimeError, match="no answer"):
                await _run_codex_cli("analyze this", [Path("/tmp/s.jpg")])


class TestStdinIsClosed:
    """All three CLIs append piped stdin to the prompt when stdin is not a
    terminal — codex documents it as a `<stdin>` block. Under uvicorn stdin is
    inherited from the launching shell, so it has to be closed explicitly."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("runner,stdout", [
        (_run_claude_cli, b"ok"),
        (_run_agy_cli, None),
    ])
    async def test_stdin_is_devnull(self, runner, stdout):
        proc = make_proc(stdout=stdout if stdout is not None else agy_envelope("ok"), returncode=0)
        with patch(
            "agent.services.video_reviewer.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=proc),
        ) as mock_exec:
            await runner("hello")
        assert mock_exec.call_args.kwargs["stdin"] == asyncio.subprocess.DEVNULL

    @pytest.mark.asyncio
    async def test_codex_stdin_is_devnull(self):
        captured = {}
        with patch(
            "agent.services.video_reviewer.asyncio.create_subprocess_exec",
            new=AsyncMock(side_effect=fake_codex_exec(captured)),
        ):
            await _run_codex_cli("analyze this", [Path("/tmp/s.jpg")])
        assert captured["kwargs"]["stdin"] == asyncio.subprocess.DEVNULL


# ---------------------------------------------------------------------------
# Timeout path (shared by all three runners via _communicate_with_timeout)
# ---------------------------------------------------------------------------

class TestCliTimeout:
    @pytest.mark.asyncio
    async def test_claude_cli_timeout_kills_proc_and_raises(self):
        proc = make_proc(stdout=b"", stderr=b"", returncode=0)

        async def fake_wait_for(coro, timeout):
            # Close the real coroutine passed in (e.g. proc.communicate()) so
            # it doesn't leak a "coroutine was never awaited" warning.
            coro.close()
            raise asyncio.TimeoutError

        with patch(
            "agent.services.video_reviewer.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=proc),
        ), patch(
            "agent.services.video_reviewer.asyncio.wait_for",
            new=AsyncMock(side_effect=fake_wait_for),
        ):
            with pytest.raises(RuntimeError) as excinfo:
                await _run_claude_cli("hello")

        proc.kill.assert_called_once()
        assert "claude" in str(excinfo.value)
        assert "timed out" in str(excinfo.value)


# ---------------------------------------------------------------------------
# _analyze_cli prompt branching per provider
# ---------------------------------------------------------------------------

EMPTY_REVIEW = '{"dimensions": {}, "errors": [], "usable_segments": []}'


def capture_runner(captured):
    """Stand in for a claude/agy runner, recording prompt and per-role kwargs."""
    async def _run(full_prompt, **kwargs):
        captured["prompt"] = full_prompt
        captured.update(kwargs)
        return EMPTY_REVIEW
    return _run


class TestAnalyzeCliPromptBranching:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "provider,runner_name", [("claude", "_run_claude_cli"), ("agy", "_run_agy_cli")]
    )
    async def test_claude_agy_providers_include_read_the_images_at(self, provider, runner_name):
        captured = {}
        contact_sheets = [Path("/tmp/sheet_00.jpg"), Path("/tmp/sheet_01.jpg")]
        with patch("agent.services.video_reviewer.config.CLI_PROVIDERS", {"active": provider}), \
             patch("agent.services.video_reviewer._build_prompt", return_value="BASE_PROMPT"), \
             patch(f"agent.services.video_reviewer.{runner_name}",
                   new=AsyncMock(side_effect=capture_runner(captured))):
            result = await _analyze_cli(contact_sheets, 10, 4.0, {}, timestamped=True)

        assert "Read the images at:" in captured["prompt"]
        assert str(contact_sheets[0]) in captured["prompt"]
        assert str(contact_sheets[1]) in captured["prompt"]
        assert "BASE_PROMPT" in captured["prompt"]
        # The sheets live outside the server cwd, so the directory holding them
        # is named to the CLI rather than left to be discovered.
        assert captured["add_dirs"] == (str(contact_sheets[0].parent),)
        assert result == {"dimensions": {}, "errors": [], "usable_segments": []}

    @pytest.mark.asyncio
    async def test_only_agy_gets_the_file_read_steering(self):
        """The steering line is what makes agy read the sheet with its
        file-reading tool instead of shelling out and being auto-denied. claude
        needs no such nudge, and an extra instruction is an extra thing for it
        to obey oddly."""
        prompts = {}
        for provider, runner_name in [("claude", "_run_claude_cli"), ("agy", "_run_agy_cli")]:
            captured = {}
            with patch("agent.services.video_reviewer.config.CLI_PROVIDERS", {"active": provider}), \
                 patch("agent.services.video_reviewer._build_prompt", return_value="BASE_PROMPT"), \
                 patch(f"agent.services.video_reviewer.{runner_name}",
                       new=AsyncMock(side_effect=capture_runner(captured))):
                await _analyze_cli([Path("/tmp/s.jpg")], 9, 4.0, {}, timestamped=True)
            prompts[provider] = captured["prompt"]

        assert "Do NOT run any shell command" in prompts["agy"]
        assert "file-reading tool" in prompts["agy"]
        assert "Do NOT run any shell command" not in prompts["claude"]

    @pytest.mark.asyncio
    async def test_codex_provider_excludes_read_the_image_at(self):
        captured = {}

        async def fake_run_codex(full_prompt, contact_sheets, **kwargs):
            captured["prompt"] = full_prompt
            captured.update(kwargs)
            return EMPTY_REVIEW

        contact_sheets = [Path("/tmp/sheet_00.jpg"), Path("/tmp/sheet_01.jpg")]
        with patch("agent.services.video_reviewer.config.CLI_PROVIDERS", {"active": "codex"}), \
             patch("agent.services.video_reviewer._build_prompt", return_value="BASE_PROMPT"), \
             patch("agent.services.video_reviewer._run_codex_cli", new=AsyncMock(side_effect=fake_run_codex)):
            result = await _analyze_cli(contact_sheets, 10, 4.0, {}, timestamped=True)

        assert "Read the image at" not in captured["prompt"]
        assert "sequential contact sheets" in captured["prompt"]
        assert "BASE_PROMPT" in captured["prompt"]
        assert result == {"dimensions": {}, "errors": [], "usable_segments": []}

    @pytest.mark.asyncio
    async def test_single_sheet_wrapper_wording_matches_original_singular_form(self):
        """With exactly 1 sheet, the wrapper sentence must read like the original
        pre-multi-sheet prompt ('Read the image at <p>. It is a contact sheet of...') —
        not the plural 'Read the images at: <p>, in that order. These are 1 sequential
        contact sheets...' which is both grammatically wrong and misleading.
        """
        captured = {}
        contact_sheets = [Path("/tmp/sheet_00.jpg")]
        with patch("agent.services.video_reviewer.config.CLI_PROVIDERS", {"active": "claude"}), \
             patch("agent.services.video_reviewer._build_prompt", return_value="BASE_PROMPT"), \
             patch("agent.services.video_reviewer._run_claude_cli",
                   new=AsyncMock(side_effect=capture_runner(captured))):
            await _analyze_cli(contact_sheets, 9, 4.0, {}, timestamped=True)

        assert captured["prompt"].startswith(f"Read the image at {contact_sheets[0]}.")
        assert "Read the images at:" not in captured["prompt"]
        assert "sequential contact sheets" not in captured["prompt"]
        assert "It is a contact sheet of 9 video frames at 4.0fps with timestamps." in captured["prompt"]

    @pytest.mark.asyncio
    async def test_untimestamped_sheets_hand_the_model_the_arithmetic(self):
        """Every review answer is expressed in time ranges. When the ffmpeg
        build cannot burn timestamps in, the prompt must stop claiming they are
        there and give the frame interval instead, or the model invents times
        off labels that do not exist."""
        captured = {}
        with patch("agent.services.video_reviewer.config.CLI_PROVIDERS", {"active": "claude"}), \
             patch("agent.services.video_reviewer._build_prompt", return_value="BASE_PROMPT"), \
             patch("agent.services.video_reviewer._run_claude_cli",
                   new=AsyncMock(side_effect=capture_runner(captured))):
            await _analyze_cli([Path("/tmp/s.jpg")], 9, 4.0, {}, timestamped=False)

        assert "with timestamps" not in captured["prompt"]
        assert "without timestamps" in captured["prompt"]
        assert "0.25s" in captured["prompt"]  # 1/4fps

    @pytest.mark.asyncio
    async def test_role_model_and_effort_reach_the_runner(self):
        captured = {}
        cfg = {"active": "agy", "roles": {"video_review": {
            "provider": "claude", "model": "sonnet", "effort": "high"}}}
        with patch("agent.services.video_reviewer.config.CLI_PROVIDERS", cfg), \
             patch("agent.services.video_reviewer._build_prompt", return_value="BASE_PROMPT"), \
             patch("agent.services.video_reviewer._run_claude_cli",
                   new=AsyncMock(side_effect=capture_runner(captured))):
            await _analyze_cli([Path("/tmp/s.jpg")], 9, 4.0, {}, timestamped=True)

        # The role entry wins over `active`, and both knobs reach the runner.
        assert captured["model"] == "sonnet"
        assert captured["effort"] == "high"


# ---------------------------------------------------------------------------
# _build_prompt :: sheet_note behavior (single-sheet vs multi-sheet)
# ---------------------------------------------------------------------------

class TestBuildPromptSheetNote:
    def test_single_sheet_has_no_sheet_note(self):
        result = _build_prompt(9, 4.0, 1, {"prompt": "", "video_prompt": ""})
        assert "sequential contact sheets" not in result

    def test_multi_sheet_includes_sheet_note(self):
        result = _build_prompt(32, 4.0, 4, {"prompt": "", "video_prompt": ""})
        assert "4 sequential contact sheets" in result
        assert "sheet 1 is earliest" in result
        assert "sheet 4 is latest" in result


# ---------------------------------------------------------------------------
# agent/api/providers.py :: patch_providers
# ---------------------------------------------------------------------------

FAKE_AGY_CATALOG = [
    {"id": "gemini-3.8-flash-low", "label": "Gemini 3.8 Flash (Low)"},
    {"id": "gemini-3.1-pro-high", "label": "Gemini 3.1 Pro (High)"},
]


@pytest.fixture
def providers_file(monkeypatch, tmp_path):
    """Point the API at a throwaway providers.json and isolate config."""
    tmp_file = tmp_path / "providers.json"
    tmp_file.write_text(json.dumps({"active": "claude"}))
    monkeypatch.setattr(providers_api, "_PROVIDERS_FILE", tmp_file)
    monkeypatch.setattr(providers_api.shutil, "which", lambda binary: "/usr/local/bin/fake")
    monkeypatch.setattr(cli_providers.shutil, "which", lambda binary: "/usr/local/bin/fake")
    # Stub the catalog. Validating an agy model otherwise spawns a real
    # `agy models`, which makes these tests depend on a signed-in CLI and pass
    # in CI only because the missing binary degrades to an empty catalog.
    # Enforcement itself is covered in TestValidateRoleEntry.
    monkeypatch.setattr(
        cli_providers, "list_models",
        AsyncMock(side_effect=lambda provider, force=False: list(
            FAKE_AGY_CATALOG if provider == "agy" else [])),
    )
    # Ensure config.CLI_PROVIDERS mutation doesn't leak to other tests.
    monkeypatch.setattr(
        providers_api.config, "CLI_PROVIDERS",
        dict(providers_api.config.CLI_PROVIDERS), raising=False,
    )
    return tmp_file


class TestPatchProviders:
    @pytest.mark.asyncio
    async def test_unknown_provider_raises_400(self):
        with pytest.raises(HTTPException) as excinfo:
            await providers_api.patch_providers({"active": "not-a-real-provider"})
        assert excinfo.value.status_code == 400

    @pytest.mark.asyncio
    async def test_known_provider_missing_binary_raises_400(self, monkeypatch):
        monkeypatch.setattr(providers_api.shutil, "which", lambda binary: None)
        with pytest.raises(HTTPException) as excinfo:
            await providers_api.patch_providers({"active": "claude"})
        assert excinfo.value.status_code == 400

    @pytest.mark.asyncio
    async def test_empty_body_raises_400(self):
        with pytest.raises(HTTPException) as excinfo:
            await providers_api.patch_providers({})
        assert excinfo.value.status_code == 400

    @pytest.mark.asyncio
    async def test_known_provider_with_binary_updates_file_and_config(self, providers_file):
        result = await providers_api.patch_providers({"active": "codex"})

        assert result["status"] == "updated"
        assert result["active"] == "codex"
        assert json.loads(providers_file.read_text())["active"] == "codex"
        assert providers_api.config.CLI_PROVIDERS["active"] == "codex"

    @pytest.mark.asyncio
    async def test_legacy_active_switch_migrates_a_file_with_no_roles(self, providers_file):
        """providers.json predates roles. Switching `active` on an old file has
        to leave a roles map behind, or the dashboard shows nothing to edit."""
        result = await providers_api.patch_providers({"active": "agy"})
        assert result["roles"]["video_review"]["provider"] == "agy"
        assert json.loads(providers_file.read_text())["roles"]["video_review"]["provider"] == "agy"

    @pytest.mark.asyncio
    async def test_legacy_active_switch_clears_model_and_clamps_effort(self, providers_file):
        """A model slug is meaningless to a different CLI — agy rejects
        "sonnet" outright — and agy's effort ladder stops at high. Carrying
        either across a provider switch turns the next review into a hard CLI
        error several seconds in."""
        providers_file.write_text(json.dumps({"active": "claude", "roles": {
            "video_review": {"provider": "claude", "model": "sonnet", "effort": "max"}}}))

        result = await providers_api.patch_providers({"active": "agy"})

        entry = result["roles"]["video_review"]
        assert entry == {"provider": "agy", "model": None, "effort": None}

    @pytest.mark.asyncio
    async def test_legacy_active_switch_keeps_an_effort_the_new_provider_supports(self, providers_file):
        providers_file.write_text(json.dumps({"active": "claude", "roles": {
            "video_review": {"provider": "claude", "model": "sonnet", "effort": "high"}}}))
        result = await providers_api.patch_providers({"active": "agy"})
        assert result["roles"]["video_review"]["effort"] == "high"

    @pytest.mark.asyncio
    async def test_roles_patch_round_trips(self, providers_file):
        result = await providers_api.patch_providers({"roles": {"video_review": {
            "provider": "claude", "model": "sonnet", "effort": "high"}}})

        assert result["roles"]["video_review"] == {
            "provider": "claude", "model": "sonnet", "effort": "high"}
        assert json.loads(providers_file.read_text())["roles"]["video_review"]["model"] == "sonnet"

    @pytest.mark.asyncio
    async def test_roles_patch_rejects_model_plus_effort_for_agy(self, providers_file):
        """agy's slugs name their own effort, so the pair is either redundant or
        contradictory — and agy rejects it either way. Better a 400 here than a
        subprocess failure on the next review."""
        with pytest.raises(HTTPException) as excinfo:
            await providers_api.patch_providers({"roles": {"video_review": {
                "provider": "agy", "model": "gemini-3.8-flash-low", "effort": "low"}}})
        assert excinfo.value.status_code == 400
        assert "pick one" in excinfo.value.detail

    @pytest.mark.asyncio
    async def test_roles_patch_allows_agy_with_a_model_and_no_effort(self, providers_file):
        result = await providers_api.patch_providers({"roles": {"video_review": {
            "provider": "agy", "model": "gemini-3.8-flash-low"}}})
        assert result["roles"]["video_review"] == {
            "provider": "agy", "model": "gemini-3.8-flash-low", "effort": None}

    @pytest.mark.asyncio
    async def test_active_and_roles_in_one_body_keeps_the_explicit_role(self, providers_file):
        """The handler advertises "active, roles, or both". The whole-agent
        sweep must not undo a role the same request named: that entry is the
        more specific instruction and it already passed validation."""
        result = await providers_api.patch_providers({
            "active": "codex",
            "roles": {"video_review": {
                "provider": "codex", "model": "gpt-5.6-sol", "effort": "high"}},
        })
        assert result["active"] == "codex"
        assert result["roles"]["video_review"] == {
            "provider": "codex", "model": "gpt-5.6-sol", "effort": "high"}

    @pytest.mark.asyncio
    async def test_reasserting_the_same_provider_keeps_the_model(self, providers_file):
        """`/fk-change-provider set claude` on a config already on claude must
        be a no-op, not a quiet reset. The reason a model is dropped on a
        switch — a slug means nothing to a different CLI — does not apply when
        the CLI did not change."""
        providers_file.write_text(json.dumps({"active": "claude", "roles": {
            "video_review": {"provider": "claude", "model": "opus", "effort": "high"}}}))

        result = await providers_api.patch_providers({"active": "claude"})

        assert result["roles"]["video_review"] == {
            "provider": "claude", "model": "opus", "effort": "high"}

    @pytest.mark.asyncio
    async def test_roles_patch_rejects_an_agy_model_outside_its_catalog(self, providers_file):
        """agy's catalog is closed and it rejects anything else itself — several
        seconds into the next review, with a raw CLI error. A 400 that names the
        known slugs is the whole reason this module exists."""
        with pytest.raises(HTTPException) as excinfo:
            await providers_api.patch_providers({"roles": {"video_review": {
                "provider": "agy", "model": "gemini-9-does-not-exist"}}})
        assert excinfo.value.status_code == 400
        assert "gemini-3.8-flash-low" in excinfo.value.detail

    @pytest.mark.asyncio
    async def test_roles_patch_leaves_an_unknown_role_in_the_file_alone(self, providers_file):
        """An `active` sweep used to silently adopt a role name this build does
        not know, while the `roles` path 400s on the same name. One policy for
        both: names outside ROLES are neither rewritten nor accepted."""
        providers_file.write_text(json.dumps({"active": "claude", "roles": {
            "legacy_role": {"provider": "agy", "model": None, "effort": None},
            "video_review": {"provider": "claude", "model": None, "effort": None}}}))

        result = await providers_api.patch_providers({"active": "codex"})

        assert result["roles"]["video_review"]["provider"] == "codex"
        assert result["roles"]["legacy_role"] == {
            "provider": "agy", "model": None, "effort": None}

    @pytest.mark.asyncio
    async def test_roles_patch_keeps_active_in_step(self, providers_file):
        """`active` is what /fk-change-provider and the statusline read. If the
        dashboard can move video_review without moving `active`, those two
        report a provider that is not running."""
        await providers_api.patch_providers(
            {"roles": {"video_review": {"provider": "codex"}}}
        )
        assert json.loads(providers_file.read_text())["active"] == "codex"

    @pytest.mark.asyncio
    async def test_roles_patch_rejects_an_effort_the_provider_lacks(self, providers_file):
        with pytest.raises(HTTPException) as excinfo:
            await providers_api.patch_providers({"roles": {"video_review": {
                "provider": "agy", "effort": "xhigh"}}})
        assert excinfo.value.status_code == 400
        assert "xhigh" in excinfo.value.detail

    @pytest.mark.asyncio
    async def test_roles_patch_rejects_an_unknown_role(self, providers_file):
        with pytest.raises(HTTPException) as excinfo:
            await providers_api.patch_providers({"roles": {"nope": {"provider": "claude"}}})
        assert excinfo.value.status_code == 400
        assert "nope" in excinfo.value.detail

    @pytest.mark.asyncio
    async def test_roles_patch_accepts_an_unlisted_model_for_a_non_authoritative_cli(
        self, providers_file
    ):
        """claude takes aliases and full model names, codex takes slugs newer
        than its on-disk cache. Validating those against a catalog would break
        the day a new model ships."""
        result = await providers_api.patch_providers({"roles": {"video_review": {
            "provider": "claude", "model": "claude-something-not-in-any-catalog"}}})
        assert result["roles"]["video_review"]["model"] == "claude-something-not-in-any-catalog"


class TestGetProviders:
    @pytest.mark.asyncio
    async def test_reports_efforts_and_roles_without_probing(self, providers_file):
        """live=false must not spawn anything — the dashboard polls this."""
        with patch.object(providers_api, "_probe_version", new=AsyncMock()) as probe:
            body = await providers_api.get_providers()
        probe.assert_not_called()

        assert body["providers"]["agy"]["efforts"] == ["low", "medium", "high"]
        assert "xhigh" in body["providers"]["claude"]["efforts"]
        assert body["providers"]["agy"]["catalog_is_authoritative"] is True
        assert body["providers"]["claude"]["catalog_is_authoritative"] is False
        assert body["roles"]["video_review"]["provider"] == "claude"
        assert "video_review" in body["role_meta"]

    @pytest.mark.asyncio
    async def test_unknown_provider_models_raises_400(self):
        with pytest.raises(HTTPException) as excinfo:
            await providers_api.get_provider_models(provider="nope", refresh=False)
        assert excinfo.value.status_code == 400


# ---------------------------------------------------------------------------
# agent/services/cli_providers.py :: role resolution
# ---------------------------------------------------------------------------

class TestResolveRole:
    def test_falls_back_to_legacy_active_when_the_role_is_absent(self, monkeypatch):
        """An untouched providers.json has no `roles` key at all."""
        monkeypatch.setattr(cli_providers.config, "CLI_PROVIDERS", {"active": "codex"})
        assert cli_providers.resolve_role("video_review") == {
            "provider": "codex", "model": None, "effort": None}

    def test_role_entry_wins_over_active(self, monkeypatch):
        monkeypatch.setattr(cli_providers.config, "CLI_PROVIDERS", {
            "active": "claude",
            "roles": {"video_review": {"provider": "agy", "model": "m", "effort": "high"}}})
        assert cli_providers.resolve_role("video_review") == {
            "provider": "agy", "model": "m", "effort": "high"}

    def test_unknown_provider_degrades_to_the_default(self, monkeypatch):
        """Hand-edited config should not take the review path down with a
        KeyError deep inside the runner dispatch."""
        monkeypatch.setattr(cli_providers.config, "CLI_PROVIDERS", {"active": "gemini"})
        assert cli_providers.resolve_role("video_review")["provider"] == "claude"

    def test_effort_outside_the_ladder_is_dropped_not_forwarded(self, monkeypatch):
        """agy rejects xhigh. Forwarding it costs a subprocess round trip to
        learn what the ladder already says here."""
        monkeypatch.setattr(cli_providers.config, "CLI_PROVIDERS", {
            "roles": {"video_review": {"provider": "agy", "effort": "xhigh"}}})
        assert cli_providers.resolve_role("video_review")["effort"] is None

    def test_empty_config_still_resolves(self, monkeypatch):
        monkeypatch.setattr(cli_providers.config, "CLI_PROVIDERS", {})
        assert cli_providers.resolve_role("video_review")["provider"] == "claude"


@pytest.fixture
def fake_binaries(monkeypatch):
    monkeypatch.setattr(cli_providers.shutil, "which", lambda b: "/bin/fake")


class TestValidateRoleEntry:
    @pytest.mark.asyncio
    async def test_missing_binary_is_rejected(self, monkeypatch):
        monkeypatch.setattr(cli_providers.shutil, "which", lambda b: None)
        with pytest.raises(ValueError, match="not found on PATH"):
            await cli_providers.validate_role_entry("video_review", {"provider": "claude"})

    @pytest.mark.asyncio
    async def test_non_string_model_is_rejected(self, fake_binaries):
        with pytest.raises(ValueError, match="string or null"):
            await cli_providers.validate_role_entry(
                "video_review", {"provider": "claude", "model": 7})

    @pytest.mark.asyncio
    async def test_a_model_starting_with_a_dash_is_rejected(self, fake_binaries):
        """Models are unvalidated for the open-catalog providers on purpose,
        and the value lands in argv right after --model. Nothing legitimate
        starts with a dash."""
        with pytest.raises(ValueError, match="must not start with"):
            await cli_providers.validate_role_entry(
                "video_review",
                {"provider": "claude", "model": "--dangerously-skip-permissions"},
            )

    @pytest.mark.asyncio
    async def test_blank_model_and_effort_normalise_to_none(self, fake_binaries):
        """The dashboard's "Default" option sends an empty value; it must mean
        "let the CLI decide", not an empty --model argument."""
        assert await cli_providers.validate_role_entry(
            "video_review", {"provider": "claude", "model": "", "effort": ""}
        ) == {"provider": "claude", "model": None, "effort": None}

    @pytest.mark.asyncio
    async def test_an_unknown_model_is_rejected_where_the_catalog_is_closed(
        self, fake_binaries
    ):
        """agy validates --model itself and errors out several seconds into the
        run. Catching it here is the difference between a 400 that names the
        options and a failed review."""
        with patch.object(cli_providers, "list_models", new=AsyncMock(
                return_value=[{"id": "gemini-3.8-flash-low", "label": "x"}])):
            with pytest.raises(ValueError, match="Unknown agy model"):
                await cli_providers.validate_role_entry(
                    "video_review", {"provider": "agy", "model": "gemini-9-nope"})

    @pytest.mark.asyncio
    async def test_an_unknown_model_passes_where_the_catalog_is_open(self, fake_binaries):
        """claude takes aliases and full names, codex takes slugs newer than
        its cache. Validating those would break the day a new model ships."""
        with patch.object(cli_providers, "list_models", new=AsyncMock(return_value=[])):
            entry = await cli_providers.validate_role_entry(
                "video_review", {"provider": "claude", "model": "claude-brand-new"})
        assert entry["model"] == "claude-brand-new"

    @pytest.mark.asyncio
    async def test_an_empty_catalog_does_not_block_the_write(self, fake_binaries):
        """Emptiness means the listing call failed, not that agy has no models.
        Blocking on it would make a transient `agy models` failure look like a
        rejected setting."""
        with patch.object(cli_providers, "list_models", new=AsyncMock(return_value=[])):
            entry = await cli_providers.validate_role_entry(
                "video_review", {"provider": "agy", "model": "gemini-3.8-flash-low"})
        assert entry["model"] == "gemini-3.8-flash-low"


# ---------------------------------------------------------------------------
# agent/services/cli_providers.py :: model catalogs
# ---------------------------------------------------------------------------

class TestModelCatalogs:
    @pytest.mark.asyncio
    async def test_agy_catalog_skips_the_header_line(self, monkeypatch):
        """`agy models` prints "Fetching available models..." before the real
        rows. Only the tab-separated lines are models."""
        stdout = (
            b"Fetching available models...\n"
            b"gemini-3.8-flash-low\tGemini 3.8 Flash (Low)\n"
            b"claude-sonnet-4-6\tClaude Sonnet 4.6 (Thinking)\n"
        )
        proc = make_proc(stdout=stdout, returncode=0)
        monkeypatch.setattr(cli_providers.shutil, "which", lambda b: "/bin/fake")
        with patch("agent.services.cli_providers.asyncio.create_subprocess_exec",
                   new=AsyncMock(return_value=proc)):
            models = await cli_providers.list_models("agy", force=True)

        assert models == [
            {"id": "gemini-3.8-flash-low", "label": "Gemini 3.8 Flash (Low)"},
            {"id": "claude-sonnet-4-6", "label": "Claude Sonnet 4.6 (Thinking)"},
        ]

    @pytest.mark.asyncio
    async def test_a_failed_listing_is_an_empty_list_not_an_exception(self, monkeypatch):
        """The dashboard asks for this on every provider change. A missing or
        broken CLI must degrade to "no catalog", not 500 the settings page."""
        proc = make_proc(stdout=b"", stderr=b"boom", returncode=1)
        monkeypatch.setattr(cli_providers.shutil, "which", lambda b: "/bin/fake")
        with patch("agent.services.cli_providers.asyncio.create_subprocess_exec",
                   new=AsyncMock(return_value=proc)):
            assert await cli_providers.list_models("agy", force=True) == []

    @pytest.mark.asyncio
    async def test_a_missing_binary_is_an_empty_list(self, monkeypatch):
        monkeypatch.setattr(cli_providers.shutil, "which", lambda b: None)
        assert await cli_providers.list_models("agy", force=True) == []

    @pytest.mark.asyncio
    async def test_an_empty_catalog_is_not_cached(self, monkeypatch):
        """Emptiness here always means a transient failure, so caching it would
        wedge the picker for five minutes after the CLI comes back."""
        monkeypatch.setattr(cli_providers.shutil, "which", lambda b: "/bin/fake")
        cli_providers.clear_catalog_cache()

        fail = make_proc(stdout=b"", stderr=b"boom", returncode=1)
        with patch("agent.services.cli_providers.asyncio.create_subprocess_exec",
                   new=AsyncMock(return_value=fail)):
            assert await cli_providers.list_models("agy") == []

        ok = make_proc(stdout=b"x\tX\n", returncode=0)
        with patch("agent.services.cli_providers.asyncio.create_subprocess_exec",
                   new=AsyncMock(return_value=ok)):
            assert await cli_providers.list_models("agy") == [{"id": "x", "label": "X"}]
        cli_providers.clear_catalog_cache()

    def test_codex_catalog_hides_models_codex_hides(self, monkeypatch, tmp_path):
        """`codex models` cannot run headlessly ("stdin is not a terminal"), so
        its own cache is the only listing available — and it marks some entries
        hidden, which are not offerable."""
        cache = tmp_path / "models_cache.json"
        cache.write_text(json.dumps({"models": [
            {"slug": "gpt-5.6-sol", "display_name": "GPT-5.6-Sol", "visibility": "list",
             "supported_reasoning_levels": [{"effort": "low"}, {"effort": "high"}]},
            {"slug": "gpt-reserve", "display_name": "GPT-Reserve", "visibility": "hide"},
        ]}))
        monkeypatch.setattr(cli_providers, "_CODEX_MODELS_CACHE", cache)

        models = cli_providers._list_codex_models()
        assert [m["id"] for m in models] == ["gpt-5.6-sol"]
        assert models[0]["efforts"] == ["low", "high"]

    def test_codex_catalog_without_a_cache_file_is_empty(self, monkeypatch, tmp_path):
        monkeypatch.setattr(cli_providers, "_CODEX_MODELS_CACHE", tmp_path / "nope.json")
        assert cli_providers._list_codex_models() == []


# ---------------------------------------------------------------------------
# ffmpeg drawtext fallback
# ---------------------------------------------------------------------------

# Real rows from `ffmpeg -hide_banner -filters`, kept verbatim: the probe is a
# regex over this exact shape and has never been run against it in a test.
_FILTERS_WITH_DRAWTEXT = """\
Filters:
  T.. = Timeline support
 ... drawbox           V->V       Draw a colored box on the input video.
 T.C drawtext          V->V       Draw text on top of video frames using libfreetype library.
 ... scale             V->V       Scale the input video size and/or convert the image format.
"""

_FILTERS_WITHOUT_DRAWTEXT = """\
Filters:
  T.. = Timeline support
 ... drawbox           V->V       Draw a colored box on the input video.
 ... drawgraph         V->V       Draw a graph using input video metadata.
 ... scale             V->V       Scale the input video size and/or convert the image format.
"""


class TestHasDrawtext:
    """The one function whose misbehaviour re-breaks every review. Both
    _frame_filter tests stub it out, so without this its regex never runs
    against real `ffmpeg -filters` output."""

    @staticmethod
    def _probe(stdout, returncode=0):
        import agent.services.video_reviewer as vr
        vr._has_drawtext.cache_clear()
        completed = MagicMock(stdout=stdout, stderr="", returncode=returncode)
        try:
            with patch("agent.services.video_reviewer.subprocess.run", return_value=completed):
                return vr._has_drawtext()
        finally:
            vr._has_drawtext.cache_clear()

    def test_finds_drawtext_in_a_real_filter_listing(self):
        assert self._probe(_FILTERS_WITH_DRAWTEXT) is True

    def test_absent_drawtext_is_detected(self):
        assert self._probe(_FILTERS_WITHOUT_DRAWTEXT) is False

    def test_a_description_mentioning_drawtext_is_not_a_match(self):
        """The filter name is the second whitespace-delimited token. Matching
        anywhere on the line would make any filter whose description mentions
        drawtext a false positive — and a false positive here puts an absent
        filter back into the chain, which aborts extraction entirely."""
        listing = " ... overlay           V->V       Like drawtext but for images.\n"
        assert self._probe(listing) is False

    def test_an_ffmpeg_that_cannot_be_run_reports_no_drawtext(self):
        """Fail safe: an unusable ffmpeg must not claim the filter is there."""
        import agent.services.video_reviewer as vr
        vr._has_drawtext.cache_clear()
        try:
            with patch("agent.services.video_reviewer.subprocess.run",
                       side_effect=OSError("no ffmpeg")):
                assert vr._has_drawtext() is False
        finally:
            vr._has_drawtext.cache_clear()


class TestFrameFilter:
    def test_includes_drawtext_when_ffmpeg_has_it(self, monkeypatch):
        monkeypatch.setattr("agent.services.video_reviewer._has_drawtext", lambda: True)
        chain = _frame_filter(4.0)
        assert chain.startswith("fps=4.0,scale=320:-1,drawtext=")
        assert "%{pts\\:hms}" in chain

    def test_omits_drawtext_when_ffmpeg_lacks_it(self, monkeypatch):
        """Homebrew's ffmpeg 8.x ships without libfreetype. Naming a filter
        that does not exist aborts the whole chain with "No such filter", which
        took down frame extraction and therefore every review — not just the
        timestamps."""
        monkeypatch.setattr("agent.services.video_reviewer._has_drawtext", lambda: False)
        assert _frame_filter(4.0) == "fps=4.0,scale=320:-1"

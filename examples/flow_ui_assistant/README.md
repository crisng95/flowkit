# Example: Flow web worker for assistant video jobs

Render an Omni first/last-frame scene through the signed-in Flow web composer and let the existing `assistant` provider write the result to the scene. This example uses Flow's displayed credits and its own Generate and Download controls. It does not need the Flow Kit browser extension, access to browser credentials, or changes to the core providers.

The example has two halves: `worker.py` holds a job lease and returns the downloaded file to FlowKit; `browser.js` is loaded by an active browser operator (tested with Codex) that can use the signed-in tab. It is not a standalone browser daemon. Use the Simplified Chinese Flow interface; the browser labels and selectors in this example are pinned to that interface. Expect it to stop if the Flow controls change.

## Prerequisites

- Run FlowKit and this example on the same machine. Use Python 3.10+ and put `ffprobe` and `ffmpeg` on `PATH`.
- Open an existing Flow project in a normally signed-in browser with the Flow Kit extension disabled for the test. In FlowKit, use a project with that same `flow_project_id`, `video_model_family: omni_flash`, and a scene with a duration of 4, 6, 8 or 10 seconds. Both scene frames must already exist in the Flow project. Use a linked child scene for the tail frame so the batch producer can resolve `end_url`.
- Copy `config.example.json` outside the repository and replace its project UUID, frame media UUIDs and exact Flow asset names. The start and end UUIDs must match the ones already on the scene and its chain. Set the model, resolution, and maximum credits per job. In the Flow composer select Video → Frames, choose the matching aspect, model and duration, and set `x1`. Leave the composer empty.
- Keep a single worker on the test queue so another `assistant` worker does not take the job. This example handles an explicit request ID and ignores unrelated jobs.

## Walkthrough

Run the following from the repository root. Keep the state directory outside the checkout and retain it while FlowKit references its outputs. Add `--api http://127.0.0.1:<port>/api` before a subcommand if using a custom port.

1. Submit the scene through the normal `POST /api/requests/batch` endpoint. Example body (replace the IDs):

   ```json
   {
     "requests": [{
       "type": "GENERATE_VIDEO",
       "provider": "assistant",
       "orientation": "VERTICAL",
       "project_id": "<project-id>",
       "video_id": "<video-id>",
       "scene_id": "<scene-id>"
     }]
   }
   ```

2. Take the ID returned by the batch request. When `GET /api/provider-jobs/<request-id>` reports `QUEUED`, claim it:

   ```bash
   python examples/flow_ui_assistant/worker.py --state-dir /path/to/state claim REQUEST_ID --config /path/to/config.json
   ```

   Load `browser.js` in the browser operator, create `const worker = createFlowUiWorker(tab)` with the signed-in project tab, and pass the claim command's JSON output to `await worker.prepare(job)`. It checks the project, frames, composer settings and displayed credits before submission.

3. Record a submit intent and then invoke `await worker.submit(job)` **once**:

   ```bash
   python examples/flow_ui_assistant/worker.py --state-dir /path/to/state mark-submit REQUEST_ID
   ```

   If the click times out, inspect `await worker.status(job)` and the existing Flow result. Do not submit a second time. For longer waits, run `heartbeat REQUEST_ID` about every 100 seconds to renew the worker lease. Stop on Flow warnings or a challenge. Do not automate a challenge or switch to another provider on failure. `fail REQUEST_ID --reason ...` can report a known failure on the live lease; the example will not reclaim a job it has handled.

4. When `await worker.status(job)` reports `ready`, call `await worker.requestDownload(job)` once. Identify the new MP4 in Chrome's configured download directory using the returned timestamp. Complete the job with that file:

   ```bash
   python examples/flow_ui_assistant/worker.py --state-dir /path/to/state complete REQUEST_ID --video /path/to/download.mp4
   ```

   The helper checks size, duration and full decode, stages the MP4 and reports its `file://` URL to the provider job. Check `GET /api/requests/<request-id>` and `GET /api/scenes/<scene-id>`: the request and scene video status should be `COMPLETED` with the same media UUID and file URL. The example never patches the scene to set the result.

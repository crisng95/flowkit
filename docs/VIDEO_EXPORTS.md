# Video exports

FlowKit treats output quality as an explicit export/download choice rather than
an implementation detail.

## Omni Flash

Gemini Omni Flash generation normally produces a 720p source video. Google Flow
provides a native Full HD export for that result. FlowKit exposes it directly as
**Export 1080p**; internally Google names the operation an upsample, but callers
do not need to reason about that implementation detail.

## Export Full HD (recommended)

```bash
curl -sS -X POST http://127.0.0.1:8100/api/flow/export-video \
  -H 'Content-Type: application/json' \
  -d '{
    "media_id": "<COMPLETED_VIDEO_MEDIA_ID>",
    "scene_id": "job-1",
    "quality": "1080p",
    "aspect_ratio": "VIDEO_ASPECT_RATIO_LANDSCAPE"
  }'
```

`quality` defaults to `1080p`. `4k` remains an explicit API option, but it is plan-gated by Google Flow; the currently verified account exposes 4K as disabled while 1080p is available.

The response contains `flowkitPolling.workflows`. Poll those descriptors:

```bash
curl -sS -X POST http://127.0.0.1:8100/api/flow/check-status \
  -H 'Content-Type: application/json' \
  -d '{"mode":"export","workflows": <FLOWKIT_POLLING_WORKFLOWS>}'
```

When `download_ready` becomes `true`, use
`workflows[].media.url` immediately. It is a short-lived signed
`flow-content.google` URL.

## Compatibility

`POST /api/flow/upscale-video` remains the low-level submit surface. New integrations should use `export-video`, then poll the returned workflows through the existing `POST /api/flow/check-status` endpoint with `mode: "export"`. This keeps all Flow polling behind one API surface.

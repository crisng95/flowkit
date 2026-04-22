# Redis Job Contract

## Decision

Use **Redis Streams** for all queues.

Reason:

- consumer groups
- ack semantics
- pending inspection
- replay support
- dead-letter routing

This contract is the canonical format for:

- control API
- scheduler
- lane runner
- requeue tools

## Queue Keys

### Global

- `chapters:pending`
  - chapter scheduling requests

### Per lane

- `lane:01:jobs`
- `lane:02:jobs`
- `lane:03:jobs`
- `lane:04:jobs`
- `lane:05:jobs`
- `lane:06:jobs`
- `lane:07:jobs`
- `lane:08:jobs`
- `lane:09:jobs`
- `lane:10:jobs`

### Per lane dead-letter streams

- `lane:01:dead`
- `lane:02:dead`
- `lane:03:dead`
- `lane:04:dead`
- `lane:05:dead`
- `lane:06:dead`
- `lane:07:dead`
- `lane:08:dead`
- `lane:09:dead`
- `lane:10:dead`

### Optional control keys

- `lane:01:heartbeat`
- `lane:02:heartbeat`
- ...
- `lane:10:heartbeat`

Use heartbeat keys as JSON strings with short TTL.

## Consumer Groups

### Global scheduler stream

- Stream: `chapters:pending`
- Consumer group: `scheduler`

### Worker lane stream

- Stream: `lane:XX:jobs`
- Consumer group: `lane:XX`

Worker consumer name format:

- `fk-w01`
- `fk-w02`
- ...
- `fk-w10`

## Message Envelope

Every stream message must include the same top-level fields.

### Required fields

- `job_id`
- `job_type`
- `project_id`
- `chapter_id`
- `lane_id`
- `trace_id`
- `attempt`
- `max_attempts`
- `priority`
- `idempotency_key`
- `created_at`
- `payload_json`

### Field types

- `job_id`: UUID string
- `job_type`: enum name from Postgres `job_type_enum`
- `project_id`: UUID string
- `chapter_id`: UUID string
- `lane_id`: `lane-01` ... `lane-10`
- `trace_id`: opaque tracing string
- `attempt`: integer string
- `max_attempts`: integer string
- `priority`: integer string
- `idempotency_key`: deterministic string
- `created_at`: ISO8601 UTC string
- `payload_json`: compact JSON string

## Message Examples

### Chapter scheduling request

Stream:
- `chapters:pending`

```json
{
  "project_id": "4a2c8f8d-5f45-4f68-a8be-9d33d021fca2",
  "chapter_id": "d1d9bf23-ff98-46b6-b7b2-4b8078d7f6af",
  "chapter_index": "1",
  "priority": "100",
  "target_duration_seconds": "300",
  "target_scene_count": "36",
  "material_id": "realistic",
  "created_at": "2026-04-21T12:00:00Z"
}
```

### `CREATE_PROJECT`

```json
{
  "job_id": "f3fdf4ef-3ab8-4ef7-a1da-8f5df2b8d4aa",
  "job_type": "CREATE_PROJECT",
  "project_id": "4a2c8f8d-5f45-4f68-a8be-9d33d021fca2",
  "chapter_id": "d1d9bf23-ff98-46b6-b7b2-4b8078d7f6af",
  "lane_id": "lane-01",
  "trace_id": "trace-20260421-0001",
  "attempt": "0",
  "max_attempts": "3",
  "priority": "100",
  "idempotency_key": "chapter:d1d9bf23:create-project:v1",
  "created_at": "2026-04-21T12:01:00Z",
  "payload_json": "{\"project_title\":\"Project X Chapter 01\",\"tool_name\":\"PINHOLE\",\"material\":\"realistic\"}"
}
```

### `CREATE_ENTITIES`

```json
{
  "job_id": "f8fe0288-cfd0-4d39-8741-73954895d742",
  "job_type": "CREATE_ENTITIES",
  "project_id": "4a2c8f8d-5f45-4f68-a8be-9d33d021fca2",
  "chapter_id": "d1d9bf23-ff98-46b6-b7b2-4b8078d7f6af",
  "lane_id": "lane-01",
  "trace_id": "trace-20260421-0001",
  "attempt": "0",
  "max_attempts": "2",
  "priority": "95",
  "idempotency_key": "chapter:d1d9bf23:create-entities:v1",
  "created_at": "2026-04-21T12:01:10Z",
  "payload_json": "{\"entities\":[{\"name\":\"Milo\",\"entity_type\":\"character\",\"description\":\"Orange tabby cat with blue scarf\"}]}"
}
```

### `CREATE_VIDEO`

```json
{
  "job_id": "47f14bca-4fda-4518-a5f6-321d10ae967d",
  "job_type": "CREATE_VIDEO",
  "project_id": "4a2c8f8d-5f45-4f68-a8be-9d33d021fca2",
  "chapter_id": "d1d9bf23-ff98-46b6-b7b2-4b8078d7f6af",
  "lane_id": "lane-01",
  "trace_id": "trace-20260421-0001",
  "attempt": "0",
  "max_attempts": "2",
  "priority": "90",
  "idempotency_key": "chapter:d1d9bf23:create-video:v1",
  "created_at": "2026-04-21T12:01:20Z",
  "payload_json": "{\"title\":\"Project X Chapter 01\",\"orientation\":\"VERTICAL\"}"
}
```

### `CREATE_SCENES`

```json
{
  "job_id": "75d527d0-cf0e-4b10-bec5-e441fd0f45ab",
  "job_type": "CREATE_SCENES",
  "project_id": "4a2c8f8d-5f45-4f68-a8be-9d33d021fca2",
  "chapter_id": "d1d9bf23-ff98-46b6-b7b2-4b8078d7f6af",
  "lane_id": "lane-01",
  "trace_id": "trace-20260421-0001",
  "attempt": "0",
  "max_attempts": "2",
  "priority": "85",
  "idempotency_key": "chapter:d1d9bf23:create-scenes:v1",
  "created_at": "2026-04-21T12:01:30Z",
  "payload_json": "{\"scenes\":[{\"display_order\":0,\"prompt\":\"Milo enters the market\",\"character_names\":[\"Milo\"]},{\"display_order\":1,\"prompt\":\"Milo sees a fruit stall\",\"character_names\":[\"Milo\"]}]}"
}
```

### `GEN_REFS`

```json
{
  "job_id": "1d64cb25-c2e3-4f36-a60a-41fbd6272d64",
  "job_type": "GEN_REFS",
  "project_id": "4a2c8f8d-5f45-4f68-a8be-9d33d021fca2",
  "chapter_id": "d1d9bf23-ff98-46b6-b7b2-4b8078d7f6af",
  "lane_id": "lane-01",
  "trace_id": "trace-20260421-0001",
  "attempt": "0",
  "max_attempts": "2",
  "priority": "80",
  "idempotency_key": "chapter:d1d9bf23:gen-refs:v1",
  "created_at": "2026-04-21T12:02:00Z",
  "payload_json": "{\"character_ids\":[\"1416321d-8579-4b2d-9be0-59083cdda65f\"]}"
}
```

### `GEN_IMAGES`

```json
{
  "job_id": "7cb3d281-0d89-4dd1-9ab4-e90525283ef0",
  "job_type": "GEN_IMAGES",
  "project_id": "4a2c8f8d-5f45-4f68-a8be-9d33d021fca2",
  "chapter_id": "d1d9bf23-ff98-46b6-b7b2-4b8078d7f6af",
  "lane_id": "lane-01",
  "trace_id": "trace-20260421-0001",
  "attempt": "0",
  "max_attempts": "3",
  "priority": "75",
  "idempotency_key": "chapter:d1d9bf23:gen-images:v1",
  "created_at": "2026-04-21T12:03:00Z",
  "payload_json": "{\"scene_ids\":[\"scene-001\",\"scene-002\",\"scene-003\"],\"orientation\":\"VERTICAL\"}"
}
```

### `GEN_VIDEOS`

```json
{
  "job_id": "d758362e-1328-4791-8dab-51917100a2e3",
  "job_type": "GEN_VIDEOS",
  "project_id": "4a2c8f8d-5f45-4f68-a8be-9d33d021fca2",
  "chapter_id": "d1d9bf23-ff98-46b6-b7b2-4b8078d7f6af",
  "lane_id": "lane-01",
  "trace_id": "trace-20260421-0001",
  "attempt": "0",
  "max_attempts": "2",
  "priority": "70",
  "idempotency_key": "chapter:d1d9bf23:gen-videos:v1",
  "created_at": "2026-04-21T12:04:00Z",
  "payload_json": "{\"scene_ids\":[\"scene-001\",\"scene-002\",\"scene-003\"],\"orientation\":\"VERTICAL\"}"
}
```

### `UPSCALE`

```json
{
  "job_id": "e55973c3-588a-476c-bb68-7f5e71ff4c10",
  "job_type": "UPSCALE",
  "project_id": "4a2c8f8d-5f45-4f68-a8be-9d33d021fca2",
  "chapter_id": "d1d9bf23-ff98-46b6-b7b2-4b8078d7f6af",
  "lane_id": "lane-01",
  "trace_id": "trace-20260421-0001",
  "attempt": "0",
  "max_attempts": "1",
  "priority": "60",
  "idempotency_key": "chapter:d1d9bf23:upscale:v1",
  "created_at": "2026-04-21T12:05:00Z",
  "payload_json": "{\"scene_ids\":[\"scene-001\",\"scene-002\"],\"orientation\":\"VERTICAL\",\"resolution\":\"VIDEO_RESOLUTION_4K\"}"
}
```

### `CONCAT_CHAPTER`

```json
{
  "job_id": "67e8aa6f-1f1c-40b3-9fdc-9e4434968d38",
  "job_type": "CONCAT_CHAPTER",
  "project_id": "4a2c8f8d-5f45-4f68-a8be-9d33d021fca2",
  "chapter_id": "d1d9bf23-ff98-46b6-b7b2-4b8078d7f6af",
  "lane_id": "lane-01",
  "trace_id": "trace-20260421-0001",
  "attempt": "0",
  "max_attempts": "2",
  "priority": "50",
  "idempotency_key": "chapter:d1d9bf23:concat:v1",
  "created_at": "2026-04-21T12:06:00Z",
  "payload_json": "{\"video_id\":\"video-001\",\"with_tts\":false,\"prefer_4k\":false}"
}
```

### `UPLOAD_ARTIFACTS`

```json
{
  "job_id": "11b97c89-90cf-483d-a1bc-178a42b1c465",
  "job_type": "UPLOAD_ARTIFACTS",
  "project_id": "4a2c8f8d-5f45-4f68-a8be-9d33d021fca2",
  "chapter_id": "d1d9bf23-ff98-46b6-b7b2-4b8078d7f6af",
  "lane_id": "lane-01",
  "trace_id": "trace-20260421-0001",
  "attempt": "0",
  "max_attempts": "3",
  "priority": "40",
  "idempotency_key": "chapter:d1d9bf23:upload:v1",
  "created_at": "2026-04-21T12:06:30Z",
  "payload_json": "{\"artifact_types\":[\"chapter_final\",\"manifest\",\"log_bundle\"]}"
}
```

### `ASSEMBLE_MASTER`

```json
{
  "job_id": "d1f44ff2-f96b-42cb-a346-64fa5ab6a2e6",
  "job_type": "ASSEMBLE_MASTER",
  "project_id": "4a2c8f8d-5f45-4f68-a8be-9d33d021fca2",
  "chapter_id": "00000000-0000-0000-0000-000000000000",
  "lane_id": "control",
  "trace_id": "trace-20260421-0001",
  "attempt": "0",
  "max_attempts": "2",
  "priority": "10",
  "idempotency_key": "project:4a2c8f8d:assemble-master:v1",
  "created_at": "2026-04-21T12:10:00Z",
  "payload_json": "{\"project_slug\":\"project-x\",\"chapter_artifact_uris\":[\"r2://flowkit-output/projects/project-x/chapter-01/final.mp4\",\"r2://flowkit-output/projects/project-x/chapter-02/final.mp4\"]}"
}
```

## Ack Rules

### Scheduler

For `chapters:pending`:

1. read with `XREADGROUP`
2. persist or update assignment in Postgres
3. publish lane job into `lane:XX:jobs`
4. only then `XACK chapters:pending scheduler <message-id>`

### Lane worker

For `lane:XX:jobs`:

1. read with `XREADGROUP`
2. set job `claimed`
3. update Postgres
4. perform work
5. on success:
   - persist output metadata
   - mark `completed`
   - `XACK lane:XX:jobs lane:XX <message-id>`
6. on retryable failure:
   - mark `retryable`
   - publish a new message with `attempt + 1`
   - `XACK` old message
7. on terminal failure:
   - mark `dead`
   - `XADD lane:XX:dead * ...`
   - `XACK` old message

## Idempotency Rules

Use deterministic idempotency keys:

- one logical stage per chapter must map to one key
- retries reuse same logical key version or explicitly bump version suffix

Examples:

- `chapter:<chapter-id>:gen-images:v1`
- `chapter:<chapter-id>:gen-videos:v1`
- `chapter:<chapter-id>:concat:v1`

Never create a new key for the same logical work without bumping version intentionally.

## Heartbeat Contract

Heartbeat key:

- `lane:01:heartbeat`

Value:

```json
{
  "lane_id": "lane-01",
  "worker_hostname": "fk-w01",
  "active_job_id": "7cb3d281-0d89-4dd1-9ab4-e90525283ef0",
  "active_chapter_id": "d1d9bf23-ff98-46b6-b7b2-4b8078d7f6af",
  "credits_last_seen": 812,
  "token_age_seconds": 420,
  "updated_at": "2026-04-21T12:04:18Z"
}
```

TTL:

- 30 seconds

Refresh interval:

- 10 seconds

## Dead-Letter Contract

When writing to `lane:XX:dead`, preserve the original envelope and add:

- `dead_reason`
- `dead_at`
- `last_error`

Example:

```json
{
  "job_id": "7cb3d281-0d89-4dd1-9ab4-e90525283ef0",
  "job_type": "GEN_IMAGES",
  "chapter_id": "d1d9bf23-ff98-46b6-b7b2-4b8078d7f6af",
  "lane_id": "lane-01",
  "attempt": "3",
  "max_attempts": "3",
  "dead_reason": "max_attempts_exhausted",
  "dead_at": "2026-04-21T12:09:55Z",
  "last_error": "Internal error encountered.",
  "payload_json": "{\"scene_ids\":[\"scene-001\",\"scene-002\"]}"
}
```

## Minimal Implementation Notes

### Scheduler loop

- consume `chapters:pending`
- choose lane from Postgres `lanes`
- create `jobs` rows in Postgres
- `XADD` lane stream messages

### Worker loop

- consume `lane:XX:jobs`
- deserialize `payload_json`
- call local FlowKit REST
- write artifact rows
- ack stream

### Recommended serialization

- keep every Redis stream field a string
- store complex payload only inside `payload_json`

Do not:

- spread nested fields across many Redis columns
- make Redis the source of truth for state transitions

Postgres remains source of truth.

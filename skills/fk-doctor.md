Diagnose any FlowKit error and prescribe a fix. Knows the full error taxonomy across Google Flow, the Chrome extension, the FastAPI layer, the worker, and the YouTube upload pipeline.

## When to use this skill

**TRIGGER (auto-invoke) when:**
- Any `/api/requests/*` response has `status=FAILED` or `error_message` is set
- A request has been `PROCESSING` for > 10 minutes with no progress
- `GET /health` returns `extension_connected: false`
- User reports any error string containing: `UNSAFE_GENERATION`, `QUOTA`, `not found`, `CAPTCHA`, `NO_FLOW_KEY`, `NO_FLOW_TAB`, `extension_switched`, `Failed to fetch`, `MODEL_ACCESS_DENIED`, `PAYGATE_TIER_TWO`, `invalidTags`, `quotaExceeded`, `invalid_grant`
- User asks "why did X fail", "what's wrong with the pipeline", "why is this stuck", "tại sao X lỗi", "lỗi gì vậy"
- An HTTP 4xx/5xx reaches the main agent from any endpoint under `127.0.0.1:8100`
- A YouTube upload returns `HttpError` from `googleapiclient`
- `cryptography` / architecture / import errors surface during setup

**DO NOT use when:**
- The request is still `PENDING` and hasn't been attempted yet
- The user is asking about features, not failures (route to `/fk-status` or the relevant `/fk-*` skill instead)
- The error is in user code unrelated to the FlowKit pipeline

## Usage

- `/fk-doctor` — triage mode: scan recent FAILED requests + extension health, list what's broken and how to fix
- `/fk-doctor <request_id>` — diagnose a single request by ID
- `/fk-doctor "<error message>"` — lookup a specific error string and return the handling playbook

## How to work

You are the on-call doctor for the FlowKit pipeline. Never guess — always consult the taxonomy below and the actual code. When the user reports a symptom:

1. Gather evidence (request row, extension status, processor logs, task output).
2. Classify by **error_message string content**, not HTTP status (Flow lumps many distinct failures under 400).
3. Prescribe the exact handler listed in `agent/worker/processor.py:_handle_failure` (lines 414-481) — don't invent a new one.
4. If auto-recovery should kick in but didn't, explain why (e.g. retry_count maxed, not matched by string).

## Mode 1: Triage (no args)

```bash
# Health
curl -s http://127.0.0.1:8100/health
curl -s http://127.0.0.1:8100/api/flow/status

# Recent failures
curl -s "http://127.0.0.1:8100/api/requests?status=FAILED&limit=20"

# Stuck in PROCESSING > 10 min
curl -s "http://127.0.0.1:8100/api/requests?status=PROCESSING"
```

Bucket the failures by `error_message` prefix, print a table, and for each bucket give the fix from the taxonomy.

## Mode 2: Single request (`/fk-doctor <RID>`)

```bash
curl -s http://127.0.0.1:8100/api/requests/<RID>
```

Read:
- `status` — PENDING / PROCESSING / FAILED / COMPLETED
- `error_message` — primary signal
- `retry_count` — will it retry? (MAX_RETRIES=5)
- `type` — GENERATE_IMAGE / GENERATE_VIDEO / UPSCALE_VIDEO / GENERATE_CHARACTER_IMAGE
- Linked scene_id / character_id for re-upload context

Cross-reference `error_message` against the taxonomy below. Print: **Diagnosis / Cause / Auto-handling / Manual fix**.

## Mode 3: Error string lookup (`/fk-doctor "<error>"`)

Match against taxonomy — even partial matches (`"not found"`, `"captcha"`, `"quota"`).

## Error Taxonomy

### A. Flow-native structured errors (from `data.error.details[].reason`)

| Reason | Diagnosis | Auto-handling | Manual fix |
|--------|-----------|---------------|------------|
| `PUBLIC_ERROR_UNSAFE_GENERATION` | Safety filter tripped — real people, violence, nudity, brand names | Terminal FAILED | Rewrite prompt: use alias names + physical descriptions (see memory `real-people-bypass`); remove triggers |
| `PUBLIC_ERROR_USER_QUOTA_REACHED` | Daily credits exhausted | Terminal FAILED | Wait for daily reset, or upgrade tier |
| `PUBLIC_ERROR_MODEL_ACCESS_DENIED` | Tier mismatch (TIER_ONE trying Veo 3 / Upscale) | Terminal FAILED | `GET /api/flow/credits` to check tier; `/fk-change-model` to downgrade |
| `Requested entity was not found` | Uploaded `media_id` expired (~1h TTL on uploads) | `_recover_entity_not_found` re-uploads from `image_url`, re-queues PENDING | If auto-recovery fails: manually `POST /api/upload-image`, patch `media_id` |
| `Internal error encountered` | Flow backend transient 500 | Exponential backoff: `2^retry * 10s`, capped 300s | None — wait, or retry manually after a minute |
| `reCAPTCHA failed` / (contains `captcha`) | Extension couldn't solve reCAPTCHA | Retry ≤10× without consuming `retry_count` (processor.py:454-464) | Ensure a Google Flow tab is open and focused; reload extension |

### B. HTTP status codes

| Status | Origin | When you see it |
|--------|--------|-----------------|
| **400** | Flow API | Invalid payload / UNSAFE / entity-not-found — **route by `details.reason`** |
| **401** | Flow API | Bearer token expired — extension should auto-recapture from labs.google tab |
| **403** | Extension (`background.js:432`) | `CAPTCHA_FAILED`, `NO_FLOW_TAB`, or `MODEL_ACCESS_DENIED` — read the suffix |
| **404** | Flow API | `media_id` not found — same handler as "entity not found" |
| **429** | Flow API | Rate-limit or quota — backoff; if message mentions QUOTA_REACHED, terminal |
| **500** | Flow backend **or** extension fetch exception (`background.js:504`) | Transient — retry with backoff |
| **502** | FastAPI (`agent/api/flow.py:80,92`) | Extension returned error without explicit status — treat as transient |
| **503** | FastAPI | "Extension not connected" or `NO_FLOW_KEY` — worker re-queues PENDING, waits |
| **504** | Agent | 60s WS timeout waiting for extension — transient, re-queue |

Detection lives in `agent/worker/_parsing.py:_is_error`. A result is treated as an error if ANY of these hold:
1. `result.error` is truthy
2. `result.status` is an int and `>= 400`
3. `result.data` is a dict and `data.error` is truthy

### C. Extension / transport error strings

| Error contains | Cause | Fix |
|----------------|-------|-----|
| `Extension not connected` | WS dropped or extension offline | Reload extension at `chrome://extensions`; worker auto-retries |
| `extension reconnected` / `extension disconnected` | WS bounce mid-request | Auto re-queue, `retry_count` NOT incremented |
| `extension_switched` | User switched active Flow tab | Auto re-queue |
| `NO_FLOW_KEY` | No bearer token captured | Open `labs.google/fx/tools/flow` and sign in |
| `NO_FLOW_TAB` | No Flow tab for CAPTCHA solve | Open any Flow tab |
| `Failed to fetch` | Network drop inside service worker | Auto-retry with backoff |
| WS 60s timeout | Extension hung | Reload extension; worker re-queues |

### D. YouTube upload errors (`youtube/upload.py`)

| Error | Cause | Fix |
|-------|-------|-----|
| `invalidTags` (400) | Tags exceed **500 chars with quote overhead** — tags with spaces count `+2` per tag | Trim to fit: `sum(len(t) + (2 if ' ' in t else 0) for t in tags) + (len(tags)-1) <= 500` |
| `invalidCategoryId` (400) | Unknown category_id | Use `"22"` (People & Blogs) or `"24"` (Entertainment) |
| `quotaExceeded` (403) | YT API daily 10K quota exhausted (uploads cost 1600) | Wait 24h — resets at Pacific midnight |
| `uploadLimitExceeded` (400) | Channel daily upload cap hit | Wait 24h or use another channel |
| `invalid_grant` (auth) | OAuth token revoked/expired | `python3 youtube/auth.py <channel>` |
| `scheduledPublishTimeInPast` | `publishAt` <= now | Use `auto_schedule()` or bump to next day |

### E. Setup / environment errors

| Error | Cause | Fix |
|-------|-------|-----|
| `ImportError: incompatible architecture (have 'arm64', need 'x86_64')` | Python 3.13 arch mismatch with `cryptography` | Use `python3.10` — all ML libs need it (per memory `check_skills_first`) |
| `ffprobe` exit 1 on a file still growing | File not finalized | Wait for background encode to complete |
| `curl: (7) Failed to connect to 127.0.0.1:8100` | Agent not running | `python -m agent.main` |

### F. Common symptoms → fix (quick lookup)

When the user describes a symptom in plain language, map it here first.

| Problem | Solution |
|---------|----------|
| Extension shows "Agent disconnected" | Start `python -m agent.main` |
| Extension shows "No token" | Open `labs.google/fx/tools/flow` and sign in |
| `CAPTCHA_FAILED: NO_FLOW_TAB` | Open a Google Flow tab |
| 403 `MODEL_ACCESS_DENIED` | Tier mismatch — `GET /api/flow/credits`, downgrade model in `models.json` via `/fk-change-model` |
| Scene images inconsistent across scenes | Check all refs have UUID `media_id` — run `/fk-fix-uuids` |
| `media_id` starts with `CAMS...` | Run `/fk-fix-uuids` to extract UUID from URL |
| Upscale "permission denied" | Requires `PAYGATE_TIER_TWO` account — TIER_ONE cannot upscale |
| Request stuck in PROCESSING > 10 min | Check `error_message` history; if extension dropped, reload it at `chrome://extensions` |
| "Requested entity was not found" spam | Image URLs expired — re-upload via `POST /api/upload-image` or wait for `_recover_entity_not_found` |
| Expired GCS signed URLs | Run `/fk-refresh-urls` to regenerate |
| YouTube upload `invalidTags` | Tag-char overflow — quote overhead counts (spaces → +2 per tag) |
| Python `cryptography` arch mismatch | Use `python3.10`, not `python3.13` (x86/arm64 binary mismatch) |
| `curl: (7) Failed to connect to 127.0.0.1:8100` | Agent not running — `python -m agent.main` |

## Worker retry policy (`processor.py:_handle_failure`)

Decision order — stop at first match:

1. **`"not found"` in message** → `_recover_entity_not_found()` re-uploads media, marks PENDING.
2. **`reconnected` / `disconnected` / `switched`** → PENDING, keep `retry_count`.
3. **`captcha` / `recaptcha`** → PENDING if retry_count < 10; else FAILED.
4. **Default** → increment `retry_count`; if < `MAX_RETRIES` (5), schedule retry at `now + min(2^retry * 10, 300)`s. Else FAILED.

## Output format

Always end with a prescription block:

```
=== DIAGNOSIS ===
Symptom:     <what the user observed>
Root cause:  <what actually went wrong>
Layer:       Flow | Extension | FastAPI | Worker | YouTube | Env
Auto-handler: <which branch of _handle_failure fires, or "none — terminal">

=== FIX ===
1. <step 1>
2. <step 2>
...

=== PREVENT ===
<how to avoid this next time, if applicable>
```

## What NOT to do

- Don't write throwaway retry scripts — use `/fk-refresh-urls`, `/fk-fix-uuids`, or direct API patches.
- Don't recommend `--no-verify` or suppress errors.
- Don't guess HTTP status from error message alone — read `data.error.details[].reason` and the actual `status` field.
- Don't mark a request FAILED in the DB if the worker is still retrying — let the policy run.

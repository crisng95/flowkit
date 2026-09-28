Diagnose any FlowKit error and prescribe a fix. Knows the full error taxonomy across Google Flow, the Chrome extension, the FastAPI layer, the worker, and the YouTube upload pipeline.

## When to use this skill

**TRIGGER (auto-invoke) when:**
- Any `/api/requests/*` response has `status=FAILED` or `error_message` is set
- A request has been `PROCESSING` for > 10 minutes with no progress
- `GET /health` returns `extension_connected: false`
- User reports any error string containing: `UNSAFE_GENERATION`, `QUOTA`, `not found`, `CAPTCHA`, `UNUSUAL_ACTIVITY`, `NO_AT_TOKEN`, `NO_FLOW_PROJECT`, `UNSUPPORTED_ON_BATCH_API`, `NO_FLOW_TAB`, `FLOW_TAB_DISCARDED`, `NO_INJECTION_RESULT`, `extension_switched`, `Failed to fetch`, `MODEL_ACCESS_DENIED`, `PAYGATE_TIER_TWO`, `invalidTags`, `quotaExceeded`, `invalid_grant`
- User asks "why did X fail", "what's wrong with the pipeline", "why is this stuck", "tại sao X lỗi", "lỗi gì vậy"
- An HTTP 4xx/5xx reaches the main agent from any endpoint under `127.0.0.1:8100`
- A YouTube upload returns `HttpError` from `googleapiclient`
- `cryptography` / architecture / import errors surface during setup
- A `/fk-review-video` run fails or returns nothing, or an error mentions `No such filter`, `Frame extraction failed`, `auto-denied`, `out of credits`, `CLI failed`, `CLI timed out`, `invalid model selection`

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

**Account-safety stop rule overrides normal retries:** at the first
`PUBLIC_ERROR_UNUSUAL_ACTIVITY`, suspected account/session hijack, or other
unexpected security signal, stop all automated Flow generation immediately.
CAPTCHA-bearing generation is disabled by default; `FLOW_ENABLE_CAPTCHA_GENERATION=1`
is an explicit opt-in intended only for test accounts. Unusual-activity and
extension-hijack signals persist `flow_generation_safety_hold.json`; the hold
survives agent restarts and `/api/flow/clear-hijack` cannot clear it. Generic
CAPTCHA errors fail the request without an automatic retry, and alone do not
latch this persistent hold. Distinguish an extension/agent-only failure from a
block in the manual Flow website; do not infer one from the other. Then follow
[`docs/ACCOUNT_SAFETY.md`](../docs/ACCOUNT_SAFETY.md).

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

## The transport

One path since Flow moved to `flow.google.com` (September 2026):

```bash
python3 -c "from agent.config import FLOW_PROJECT_ID; \
  print('batch | project:', FLOW_PROJECT_ID or 'UNPINNED')"
```

The agent builds an `f.req` envelope and the extension runs it inside a
signed-in `flow.google.com` tab. **No bearer token exists on this path**, so
`flow_key_present: false` in `/api/flow/status` is normal, not a fault.
Requires a Flow tab open and `FLOW_PROJECT_ID` pinned.

The `aisandbox-pa` REST path that preceded it has been removed — it needed a
`Bearer ya29.…` Flow no longer mints. If an old report mentions it, that is the
migration, not a regression.

## Error Taxonomy

### A. Flow-native structured errors (from `data.error.details[].reason`)

| Reason | Diagnosis | Auto-handling | Manual fix |
|--------|-----------|---------------|------------|
| `PUBLIC_ERROR_UNSAFE_GENERATION` | Safety filter tripped — real people, violence, nudity, brand names | Terminal FAILED | Rewrite prompt: use alias names + physical descriptions (see memory `real-people-bypass`); remove triggers |
| `PUBLIC_ERROR_USER_QUOTA_REACHED` | Daily credits exhausted | Terminal FAILED | Wait for daily reset, or upgrade tier |
| `PUBLIC_ERROR_MODEL_ACCESS_DENIED` | Tier mismatch (TIER_ONE trying Veo 3 / Upscale) | Terminal FAILED | `GET /api/flow/credits` to check tier; `/fk-change-model` to downgrade |
| `Requested entity was not found` | Uploaded `media_id` expired (~1h TTL on uploads) | `_recover_entity_not_found` re-uploads from `image_url`, re-queues PENDING | If auto-recovery fails: manually `POST /api/upload-image`, patch `media_id` |
| `Internal error encountered` | Flow backend transient 500 | Exponential backoff: `2^retry * 10s`, capped 300s | None — wait, or retry manually after a minute |
| `FLOW_CAPTCHA_GENERATION_DISABLED` | CAPTCHA-bearing generation is off by default | Terminal FAILED before the request is sent | `FLOW_ENABLE_CAPTCHA_GENERATION=1` is explicit opt-in; use only with a test account |
| `reCAPTCHA failed` / (contains `captcha`) | CAPTCHA-bearing generation failed at the extension/Flow layer | Terminal FAILED; persistent safety hold | Diagnose without resubmitting. The pre-submit marker remains held after a CAPTCHA error. |
| `FLOW_ACCOUNT_SAFETY_HOLD` | An unusual-activity or extension-hijack signal previously latched the persistent hold | Terminal FAILED; hold persists across agent restarts | Do not retry. `/api/flow/clear-hijack` cannot clear this hold. Follow [`docs/ACCOUNT_SAFETY.md`](../docs/ACCOUNT_SAFETY.md). |
| `PUBLIC_ERROR_UNUSUAL_ACTIVITY` (may appear with 403 / `reCAPTCHA evaluation failed`) | An unusual-activity / risk-evaluation response; this string alone does not establish the cause or whether manual Flow access is blocked | Stop generation; current request is terminal and the persistent hold is latched | Separate extension-only errors from a manual Flow UI block. Google recovery is unverified; do not recommend cookie clearing, IP/network changes, or a fixed wait. Follow [`docs/ACCOUNT_SAFETY.md`](../docs/ACCOUNT_SAFETY.md). |

### B. HTTP status codes

| Status | Origin | When you see it |
|--------|--------|-----------------|
| **400** | Flow API | Invalid payload / UNSAFE / entity-not-found — **route by `details.reason`** |
| **401** | Flow API | Should not happen — batchexecute authenticates in the page, not with a bearer. Check the Flow tab is signed in; see `NO_AT_TOKEN` |
| **403** | Extension (`background.js:432`) | `CAPTCHA_FAILED`, `NO_FLOW_TAB`, or `MODEL_ACCESS_DENIED` — read the suffix |
| **404** | Flow API | `media_id` not found — same handler as "entity not found" |
| **429** | Flow API | Rate-limit or quota — backoff; if message mentions QUOTA_REACHED, terminal |
| **500** | Flow backend **or** extension fetch exception (`background.js:504`) | Transient — retry with backoff |
| **502** | FastAPI (`agent/api/flow.py:80,92`) | Extension returned error without explicit status — treat as transient |
| **503** | FastAPI | "Extension not connected" — worker re-queues PENDING, waits |
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
| `NO_FLOW_TAB` | No Flow tab for CAPTCHA solve or RPC signing | Open `https://flow.google.com/` and sign in |
| `Failed to fetch` | Network drop inside service worker | Auto-retry with backoff |
| WS 60s timeout | Extension hung | Reload extension; worker re-queues |

### C2. Batch path (`flow.google.com`) errors

| Error contains | Cause | Auto-handling | Fix |
|----------------|-------|---------------|-----|
| `NO_AT_TOKEN` | The Flow tab loaded but `WIZ_global_data.SNlM0e` is absent — the page is signed out, on an interstitial, or still booting | Retried with backoff | Open `https://flow.google.com/`, confirm you are signed in, let the app finish loading |
| `NO_FLOW_TAB` | No Flow tab to sign the request | Extension opens one and retries once | Leave one signed-in Flow tab open; nothing here works headless |
| `FLOW_TAB_DISCARDED` | Chrome discarded the backgrounded tab and the reload did not revive it | Retried with backoff | Pin the Flow tab, or keep its window visible |
| `NO_INJECTION_RESULT` | `chrome.scripting.executeScript` returned no frame result; the Flow tab may have closed or still been booting | A CAPTCHA-bearing request is held for manual review; non-generation requests follow their normal error policy | Do not retry generation or mint another token. Check the tab and preserve the response, then follow [`docs/ACCOUNT_SAFETY.md`](../docs/ACCOUNT_SAFETY.md). |
| `NO_FLOW_PROJECT` | A low-level caller reached batchexecute without a project id | **Terminal — not retried** | Use `POST /api/projects` to create a real Flow project, or call a public `/api/flow/*` endpoint without `project_id` so the session-project lease resolves one automatically |
| `UNSUPPORTED_ON_BATCH_API` | A capability whose payload was never captured off the new UI, all on the Veo path: **video upscale**, **Veo r2v**, **Veo start+end-frame chaining**. Every Omni mode is ported, so this never names Omni any more | **Terminal — not retried** | For chaining and r2v, `FLOW_ALLOW_DEGRADED=1` falls back to plain i2v off the start frame. Upscale has no fallback. Real fix: capture the payload — `docs/CAPTURE.md` |
| `PUBLIC_ERROR_UNUSUAL_ACTIVITY` | Flow returned an unusual-activity / risk-evaluation error; manual UI impact is a separate observation | **Stop all automated generation immediately; current request fails and a persistent hold is latched** | Determine whether this is extension-only or the manual Flow UI is also blocked. Google recovery is unverified. See [`docs/ACCOUNT_SAFETY.md`](../docs/ACCOUNT_SAFETY.md). |
| `no ogiZ0b envelope in response` | The RPC answered but not with the payload we came for — usually a signed-out page returning an HTML redirect | Retried with backoff | Re-sign in on the Flow tab |
| `Polling timeout after Ns: Media not found.` | The job never produced media inside the budget | Terminal after `MAX_RETRIES` | The quoted complaint is a **diagnostic, not the cause** — finished jobs report it too. Check the Flow UI: if the clip is there, raise `VIDEO_POLL_TIMEOUT` |

`NO_AT_TOKEN`, `NO_FLOW_TAB` and `FLOW_TAB_DISCARDED` are profile-local, so
with several extension profiles connected the agent fails the request over to
another one before reporting it. A single such error in the log with the job
still succeeding is that failover working, not a fault.

Three behaviours on this path routinely look like bugs and are not:

- **A poll can say "Media not found." and the job still finishes.** The project
  listing is what decides; the poll is a hint. Never treat the complaint as fatal.
- **A media id arrives before the clip is fetchable.** The media record serves
  the poster image first and grows the `/video/` url in later, so a scene sits
  PENDING for a while after its id exists. Downloading on the id alone saves a
  still picture.
- **A retry does not resubmit.** A batch operation id is a bare uuid, which the
  Low Priority workflow path treats as unrecoverable and resubmits. On the batch
  path it is recoverable — the status poll finds it in the project listing — so
  a retried video request re-polls the render already running instead of paying
  for a second one.

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
| Extension shows "No token" | Expected — there is no bearer any more. Not a fault |
| `CAPTCHA_FAILED: NO_FLOW_TAB` | Open `https://flow.google.com/` — and check the extension is v0.3.0+, older builds only matched the dead labs.google URL and could not see the tab that was right there |
| 403 `MODEL_ACCESS_DENIED` | Tier mismatch — `GET /api/flow/credits`, downgrade model in `models.json` via `/fk-change-model` |
| CAPTCHA-bearing generation disabled | Default is off; `FLOW_ENABLE_CAPTCHA_GENERATION=1` is explicit opt-in for test accounts only |
| `PUBLIC_ERROR_UNUSUAL_ACTIVITY`, extension hijack, CAPTCHA error, or active safety hold | **Stop generation.** These signals latch a persistent hold. Distinguish extension-only failure from a manual Flow UI block. Google recovery is unverified; `/api/flow/clear-hijack` cannot clear the hold. See [`docs/ACCOUNT_SAFETY.md`](../docs/ACCOUNT_SAFETY.md). |
| Scene images inconsistent across scenes | Check all refs have UUID `media_id` — run `/fk-fix-uuids` |
| `media_id` starts with `CAMS...` | Run `/fk-fix-uuids` to extract UUID from URL |
| Upscale fails on every scene | On the batch path upscale is unported (`UNSUPPORTED_ON_BATCH_API`) — no upsampler rpc has been captured. On the legacy path it needs `PAYGATE_TIER_TWO` |
| Request stuck in PROCESSING > 10 min | Check `error_message` history; if extension dropped, reload it at `chrome://extensions` |
| "Requested entity was not found" spam | Image URLs expired — re-upload via `POST /api/upload-image` or wait for `_recover_entity_not_found` |
| Expired signed URLs | Run `/fk-refresh-urls` — on the batch path this re-signs every stored media id through the media rpc |
| YouTube upload `invalidTags` | Tag-char overflow — quote overhead counts (spaces → +2 per tag) |
| Python `cryptography` arch mismatch | Use `python3.10`, not `python3.13` (x86/arm64 binary mismatch) |
| `curl: (7) Failed to connect to 127.0.0.1:8100` | Agent not running — `python -m agent.main` |

### G. Video review errors (`services/video_reviewer.py`)

Review runs outside the worker — no retry policy applies, the call just raises.
Providers, models and efforts come from `agent/providers.json`; see
`/fk-change-provider`.

| Error | Cause | Fix |
|---|---|---|
| `Frame extraction failed: ... No such filter: 'drawtext'` | ffmpeg built without libfreetype. Should no longer happen — the filter is probed and skipped — so seeing it means the probe was bypassed | `ffmpeg -filters \| grep drawtext`. Absent is fine; sheets just lose their burned-in timestamps |
| `agy CLI had tools auto-denied headlessly (RunCommand) — its N-character answer cannot be trusted to have come from the images` | agy tried to shell out to read the contact sheet instead of using its file-reading tool; headless mode cannot prompt, so the tool was denied. Raised whether or not agy still produced an answer — the prompt carries the rubric, both scene prompts and the character names, which is enough to write a plausible review without ever looking at a frame | Restore the steering in `_AGY_READ_STEER`. **Do not** add `--dangerously-skip-permissions` — it auto-approves every tool including arbitrary shell commands, for a job that only reads JPEGs |
| `agy CLI returned non-JSON output: ...` | agy answered with bare prose on a zero exit code — usually a permission or startup error | Read the quoted text; it names the real problem |
| `agy CLI failed (rc=1): invalid model selection ... conflicts with --effort=` | agy's slugs name their own effort (`gemini-3.8-flash-low`), so model and effort cannot both be set | Clear one of them. The API rejects the pair with a 400; this only reaches the CLI from a hand-edited `providers.json` |
| `codex CLI failed (rc=1): ... Your workspace is out of credits` | The OpenAI workspace has no balance. `installed: true` only means the binary is on PATH | Refill, or switch the role to `claude`/`agy` |
| `codex CLI exited cleanly but wrote no answer to its output file` | codex returned success but produced nothing | Re-run; if it repeats, switch provider |
| `<provider> CLI timed out after Ns` | The review exceeded `REVIEW_CLI_TIMEOUT_S` (default 120) | Raise the env var, or lower `REVIEW_FPS_*` / `REVIEW_MAX_FRAMES` so there is less to look at |
| `review answer had an error entry with no usable severity (expected one of ['CRITICAL', 'HIGH', 'MINOR']): ...` | The model graded an error with something outside the three severities. `has_critical_errors`, the `character_consistency` cap and the fix guide all branch on that exact string, so anything else silently disables all three — the model flagged a defect and the score would not show it | Read the quoted entry. A model that keeps doing this is not following the rubric; switch the role to another one |
| `Scene <id>: review answer needed repair — N error field(s) defaulted, M usable segment(s) unreadable` (warning, not a failure) | A near-miss field name (`timeRange` for `time_range`) or a missing description. Repaired, because losing those costs context but cannot move a score | Nothing required. A rising count means the model is drifting from the rubric |
| `CLI answer had no dimensions: ...` | The CLI returned parseable JSON with no scores in it. Every dimension defaults to 5.0, so this would otherwise have become a complete, plausible "poor" review of a video nobody actually looked at | Read the quoted answer. Usually the model wrote prose around the JSON, or ran out of context — lower `REVIEW_MAX_FRAMES` or try another model |

## Worker retry policy (`processor.py:_handle_failure`)

Decision order — stop at first match:

1. **`[HIJACK]` or unusual activity** → FAILED and persist the account-safety hold.
2. **`FLOW_ACCOUNT_SAFETY_HOLD` / `FLOW_CAPTCHA_GENERATION_DISABLED`** → FAILED; no retry.
3. **`UNSUPPORTED_ON_BATCH_API` / `NO_FLOW_PROJECT`** → FAILED; no retry.
4. **`reconnected` / `disconnected` / `switched`** → PENDING, keep `retry_count`.
5. **Any other `captcha` / `recaptcha` error** → FAILED; no automatic retry.
6. **`"not found"`** → attempt `_recover_entity_not_found()` and re-queue only if recovery succeeds.
7. **Default** → increment `retry_count`; if < `MAX_RETRIES` (5), schedule retry at `now + min(2^retry * 10, 300)`s. Else FAILED.

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

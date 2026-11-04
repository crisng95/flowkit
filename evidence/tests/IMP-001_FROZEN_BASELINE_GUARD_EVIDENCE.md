# IMP-001 — FROZEN BASELINE GUARD EVIDENCE

## Task

**IMP-001 — Frozen Baseline Guard**

Branch:
`chatgpt/IMP-001-frozen-baseline-guard`

Frozen authority:
- Master: `docs/design/canonical/MASTER_AI_FILM_STUDIO_FINAL_IMPLEMENTATION_BASELINE_V1.md`
- expected SHA-256: `1ff9383d713dfaab309d3f36cc83cf05e8932c1bc07f68682e2e12a488c77287`
- freeze manifest: `docs/design/canonical/MASTER_AI_FILM_STUDIO_IMPLEMENTATION_BASELINE_V1_FREEZE_MANIFEST.md`

## Implementation

Added:
- `tools/frozen_master_guard.py`
- `tests/unit/test_frozen_master_guard.py`

Changed:
- `.github/workflows/tests.yml` — runs the frozen Master guard after dependency installation and before the unit suite.

The guard is read-only and fail-closed. It verifies:
1. canonical Master file exists;
2. freeze manifest exists;
3. actual Master SHA equals the frozen SHA compiled into the guard;
4. manifest-declared Master path equals the canonical path;
5. manifest-declared Frozen SHA-256 equals the same expected SHA;
6. manifest contains the frozen verdict.

CLI success:
`FROZEN_MASTER_GUARD=PASS`

CLI failure:
`FROZEN_MASTER_GUARD=FAIL` on stderr and non-zero exit.

## Verification

### Syntax

`python -m py_compile tools\frozen_master_guard.py tests\unit\test_frozen_master_guard.py`

Result: **PASS**

### Real frozen baseline guard

`python tools\frozen_master_guard.py`

Result:

```text
FROZEN_MASTER_GUARD=PASS
MASTER=docs/design/canonical/MASTER_AI_FILM_STUDIO_FINAL_IMPLEMENTATION_BASELINE_V1.md
SHA256=1ff9383d713dfaab309d3f36cc83cf05e8932c1bc07f68682e2e12a488c77287
```

### Targeted tests — Python 3.13 isolated repo requirements

Command:

`PYTHONUTF8=1 uv run --isolated --no-project --python 3.13 --with-requirements requirements.txt --with-requirements requirements-dev.txt python -m pytest tests/unit/test_frozen_master_guard.py -q`

Result:

```text
9 passed in 0.20s
```

Covered:
- real repository frozen baseline passes;
- isolated copied frozen baseline passes;
- missing Master fails closed;
- tampered Master fails closed;
- missing manifest fails closed;
- manifest SHA mismatch fails closed;
- manifest path mismatch fails closed;
- missing frozen verdict fails closed;
- CLI success/failure exit behavior.

Tests mutate only temporary copies under pytest `tmp_path`; the frozen Master is never modified.

### Full unit regression — Windows local characterization

First dependency-complete Python 3.13 run showed:
- 361 passed
- 6 failed
- 7 errors

The 7 setup errors were Windows default-codepage fixture writes later read as UTF-8. Re-running with `PYTHONUTF8=1` removes all seven errors and three encoding-related failures.

With `PYTHONUTF8=1`, full suite result is:

```text
371 passed
3 failed
```

The remaining three failures are pre-existing platform-specific assertions in `tests/unit/test_cli_providers.py` that construct POSIX `Path("/tmp/...")` values but run on Windows:

- `test_claude_agy_providers_include_read_the_images_at[claude-_run_claude_cli]`
- `test_claude_agy_providers_include_read_the_images_at[agy-_run_agy_cli]`
- `test_single_sheet_wrapper_wording_matches_original_singular_form`

Observed mismatch:
- expected `/tmp`
- Windows `pathlib.Path` renders `\tmp`

IMP-001 does not modify `agent/services/video_reviewer.py` or those existing tests.

### Regression excluding exactly the three known Windows/POSIX-path assertions

Command:

`PYTHONUTF8=1 uv run --isolated --no-project --python 3.13 --with-requirements requirements.txt --with-requirements requirements-dev.txt python -m pytest tests/unit -q -k "not test_claude_agy_providers_include_read_the_images_at and not test_single_sheet_wrapper_wording_matches_original_singular_form"`

Result:

```text
371 passed, 3 deselected in 27.54s
```

This is recorded as the local Windows regression result, **not** as a full-suite PASS.

The GitHub workflow runs on Ubuntu and will provide the authoritative remote full-suite result for the POSIX-specific cases.

### CI workflow syntax

The updated `.github/workflows/tests.yml` was parsed using PyYAML in an isolated environment.

Result:
`WORKFLOW_YAML=PASS`

### Diff whitespace

Implementation/governance scope was checked with git diff --cached --check against the workflow, IMP-001 guard/tests, global execution law, active state files, dependency/task planning, and IMP-001 evidence.

Result: **PASS**

A whole staged-corpus whitespace check is **not** claimed clean because the newly versioned frozen Master and historical Markdown corpus intentionally contain existing Markdown two-space hard breaks/trailing whitespace. Those immutable/frozen historical/design bytes are not rewritten merely to satisfy whitespace normalization.

### Frozen Master integrity after implementation/test

Actual SHA-256:

`1ff9383d713dfaab309d3f36cc83cf05e8932c1bc07f68682e2e12a488c77287`

Result: **UNCHANGED / PASS**

## Local task verdict

IMP-001 implementation and targeted fail-closed acceptance criteria: **PASS**

Local Windows full-suite characterization: **371 PASS / 3 known platform-specific failures**.

Remote Ubuntu CI full-suite gate: **PENDING until push/PR**.

No claim of PR/merge/MAIN VERIFIED is made in this evidence until those actions occur.

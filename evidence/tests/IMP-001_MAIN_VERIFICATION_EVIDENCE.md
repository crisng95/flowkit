# IMP-001 — MAIN VERIFICATION EVIDENCE

## Scope

Task: **IMP-001 — Frozen Baseline Guard**

Frozen Master:
- path: `docs/design/canonical/MASTER_AI_FILM_STUDIO_FINAL_IMPLEMENTATION_BASELINE_V1.md`
- canonical SHA-256: `1ff9383d713dfaab309d3f36cc83cf05e8932c1bc07f68682e2e12a488c77287`

Verified writable main:
- repository: `nguyenkhactang922-bot/flowkit`
- branch: `main`
- verified implementation main SHA: `bca229eee5a159a59cc880f48a0d62f1ac78fcc5`

Upstream repository:
- `crisng95/flowkit`
- upstream PR: #65
- upstream main merge: **NOT COMPLETE**
- blocker: upstream fork-triggered workflow requires maintainer/admin approval; approval API returned HTTP 403 for the connected account.
- This evidence does **not** claim upstream MAIN VERIFIED.

## Initial implementation

Implementation commit:
`efb3f280b4a91cde4de557283c65ecb52bac9b2b`

Fork PR:
`nguyenkhactang922-bot/flowkit#1`

PR CI:
- workflow run: `36110988101`
- conclusion: **SUCCESS**
- Python 3.10 job: **SUCCESS**
- Python 3.13 job: **SUCCESS**
- `Verify frozen Master baseline`: **SUCCESS**
- `Run unit tests`: **SUCCESS**

Exact-head review:
- no blocking findings;
- no `agent/`, `dashboard/`, or `extension/` feature-source changes in the task commit;
- frozen Master SHA matched freeze authority;
- no new token-shaped matching files were introduced relative to the task base.

PR #1 merge commit:
`ef8d333274607f64afbad27cd9f9b71956fa45d7`

## Post-merge Windows verification finding

Windows local main verification correctly found a portability defect in the first guard implementation.

Environment:
- `core.autocrlf=true`

Observed working-tree Master:
- raw SHA-256: `abb08e8114be3ace0d81ceccf8a3dea45c78a6268c64fae4c332d0644fa1e303`
- CRLF count: 6770

Git blob / canonical Master:
- bytes: 554416
- SHA-256: `1ff9383d713dfaab309d3f36cc83cf05e8932c1bc07f68682e2e12a488c77287`
- CRLF count: 0
- LF count: 6770

Proof:
- CRLF→LF normalized working-tree bytes were byte-identical to the Git blob.
- normalized working-tree SHA equaled the frozen SHA.

Therefore the failure was a Windows checkout representation issue, not semantic Master drift.

IMP-001 was **not** marked MAIN VERIFIED at that point.

## CRLF portability repair

Repair branch:
`chatgpt/IMP-001-crlf-portability`

Repair commit:
`f5d6ee1116a6485eacc0754b47abd2cdacf40d52`

Repair semantics:
- canonical frozen SHA remains unchanged;
- raw exact SHA passes directly;
- if raw bytes differ, the guard permits only `CRLF → LF` normalization;
- the normalized bytes must still hash to the exact frozen SHA;
- any other content/tamper still fails closed.

Local Windows evidence:
- real main-style CRLF checkout guard: **PASS**
- canonical SHA reported: `1ff9383d713dfaab309d3f36cc83cf05e8932c1bc07f68682e2e12a488c77287`
- raw Windows SHA reported separately: `abb08e8114be3ace0d81ceccf8a3dea45c78a6268c64fae4c332d0644fa1e303`
- normalization marker: `NEWLINE_NORMALIZED=CRLF_TO_LF`
- targeted tests: **12/12 PASS**
- CRLF checkout case: PASS
- CRLF + content tamper case: FAIL as required

The attempted broad local regression after this repair timed out in the local bridge and is **not** claimed as a PASS. Remote CI is the full regression authority for this repair.

## Repair PR and CI

Fork PR:
`nguyenkhactang922-bot/flowkit#2`

Exact head:
`f5d6ee1116a6485eacc0754b47abd2cdacf40d52`

PR workflow:
- run: `36112853918`
- conclusion: **SUCCESS**
- Python 3.10: **SUCCESS**
- Python 3.13: **SUCCESS**
- frozen Master guard: **SUCCESS**
- full unit suite: **SUCCESS**

Exact-head review:
- scope exactly two files: guard + guard tests;
- no blocking findings;
- newline normalization did not weaken semantic/content SHA enforcement.

PR #2 merge commit:
`bca229eee5a159a59cc880f48a0d62f1ac78fcc5`

## Final fork-main verification

Local Windows:
- branch: `main`
- HEAD: `bca229eee5a159a59cc880f48a0d62f1ac78fcc5`
- tracking: `fork/main`
- `fork/main`: `bca229eee5a159a59cc880f48a0d62f1ac78fcc5`
- frozen guard: **PASS**
- canonical frozen SHA: unchanged
- only unrelated local staging artifact remains untracked under `_incoming/`.

Fork-main push workflow:
- run: `36112979014`
- event: `push`
- head SHA: `bca229eee5a159a59cc880f48a0d62f1ac78fcc5`
- conclusion: **SUCCESS**
- Python 3.10 guard + full unit suite: **SUCCESS**
- Python 3.13 guard + full unit suite: **SUCCESS**

## Verdict

**IMP-001 = MAIN VERIFIED on `nguyenkhactang922-bot/flowkit:main` at `bca229eee5a159a59cc880f48a0d62f1ac78fcc5`.**

Upstream `crisng95/flowkit:main` is **not** claimed verified because PR #65 remains subject to upstream maintainer workflow approval.

## Next exact action

`CLAIM IMP-002 — CANONICAL CONTRACT PRIMITIVES`

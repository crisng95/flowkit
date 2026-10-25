# ChatGPT / Execution Bridge Global Multi-Project Execution Law

## 1. Roles

### ChatGPT Web — MAIN CODING AGENT
Owns:
- repository analysis and architecture reasoning;
- task claiming and dependency ordering;
- code/design changes;
- test/build/evidence requirements;
- verification and pass/fail decision;
- Git/PR/review/merge orchestration;
- MAIN VERIFIED decision;
- automatic selection of the next dependency-ready task.

### Execution Bridge — FileMCP / approved local bridge
Acts only as the local execution surface for:
- reading/searching/writing files;
- running PowerShell/cmd/Python/Node/npm and project tools;
- running tests/build/package/smoke/E2E;
- Git/gh operations;
- returning concrete command output/evidence.

The bridge does not own architecture, product truth, acceptance, or task status.

---

## 2. Mandatory lifecycle

Every implementation task follows:

```text
CLAIM
→ ANALYZE
→ PLAN
→ CODE
→ TEST / BUILD
→ EVIDENCE
→ VERIFY
→ PASS
→ COMMIT
→ PUSH / PR
→ REVIEW
→ MERGE MAIN
→ CHECKOUT / PULL MAIN
→ VERIFY MAIN
→ MAIN VERIFIED
→ CLAIM NEXT DEPENDENCY-READY TASK
```

Short form:

```text
CLAIM → CODE → TEST → VERIFY → COMMIT → PR → REVIEW → MERGE MAIN → DONE
```

No step may be reported as complete without evidence appropriate to that step.

---

## 3. Bootstrap / resume law

At the start or resume of a project:
1. confirm workspace path and Git root;
2. confirm branch, HEAD and `git status`;
3. read `AGENTS.md` without overriding generated/upstream rules;
4. read this law;
5. read `CURRENT_HANDOFF.md`;
6. read `PROJECT_STATE.md`;
7. read `tasks/TASK_QUEUE.md` and the active task decomposition;
8. identify `NEXT_EXACT_ACTION`;
9. resume from that action rather than restarting completed work.

Do not redo a task from the beginning when durable evidence/state already exists.

---

## 4. State files

The project keeps these durable governance surfaces current:

- `CURRENT_HANDOFF.md` — current handoff and NEXT_EXACT_ACTION.
- `PROJECT_STATE.md` — current stage, active task, important gates and verified state.
- `tasks/TASK_QUEUE.md` — task status and dependency-ready queue.
- frozen design/dependency/task documents when present.
- evidence under `evidence/`.

A state file is not proof by itself. It records conclusions supported by evidence.

---

## 5. Claim discipline

A task may be CLAIMED only when:
- all hard dependencies are VERIFIED/PASS;
- no higher-authority freeze or blocking gate prohibits implementation;
- the current branch/worktree is known;
- acceptance criteria and required evidence are identified.

Only one canonical task status may be active for the same implementation scope unless explicitly running independent parallel lanes.

---

## 6. Analysis and planning law

Before changing code:
- inspect the exact implementation surface and its callers/tests;
- preserve stronger existing implementation instead of rewriting by default;
- classify reuse as KEEP / KEEP+EXTEND / ADAPT / EXTRACT / REWRITE / REPLACE / DROP where useful;
- identify persistence/migration/security/runtime impact;
- define failure paths and negative tests;
- preserve frozen authority and canonical ownership.

For large architecture changes:
```text
idea
→ capture
→ discovery/research
→ alternatives
→ independent critique
→ source/authority reconciliation
→ frozen design
→ dependency graph
→ task decomposition
→ implementation
```

Do not jump from a raw idea directly to feature coding when design authority is not resolved.

---

## 7. Frozen-baseline law

When a Master/design baseline is frozen:
- its frozen SHA is authoritative;
- implementation must not silently edit it;
- semantic Master changes require successor/unfreeze provenance and independent re-audit;
- code may derive schemas/interfaces/tests from it but may not create competing authority;
- freeze PASS is design evidence only, not product/release readiness evidence.

A frozen-baseline guard must fail closed on Master/manifest mismatch.

---

## 8. Code-change law

- Make the smallest coherent change that closes the active task.
- Do not modify unrelated source merely to make a task appear green.
- Do not delete or shorten accepted design/history to simplify implementation.
- Avoid duplicate canonical owners, shadow truth stores and compatibility leakage.
- Keep provider-specific/runtime-specific details behind accepted adapters.
- Preserve backward compatibility through explicit anti-corruption/migration boundaries where required.
- Do not edit generated files when their source says not to; modify the generator/source instead.

---

## 9. Testing law

Testing follows the claim being made.

At minimum for a code task:
1. syntax/static validation where applicable;
2. targeted tests for the new/changed behavior;
3. negative/failure-path tests;
4. regression tests for affected existing behavior;
5. broader/full suite when feasible;
6. platform/provider/live evidence only when required by that claim.

If the full suite is blocked by a pre-existing/environment-specific failure:
- prove the failure is outside the task change;
- run the largest valid unaffected regression set;
- record the exact blocked cases;
- use CI/target-platform evidence where appropriate;
- never relabel a failing suite as PASS.

Test-file existence is not test execution evidence.

---

## 10. Evidence law

Evidence must contain the real command/result needed to support the claim.

Examples:
- test count and exit code;
- build/package output;
- SHA/hash checks;
- migration/fault-injection output;
- Git diff/status;
- PR exact head;
- CI check result;
- packaged smoke marker;
- live provider correlation/artifact IDs where explicitly required.

Do not claim PASS, build success, push, PR, merge or MAIN VERIFIED without real evidence.

---

## 11. Git law

For implementation work:
- use a task branch unless project rules explicitly require otherwise;
- inspect `git diff` and `git diff --check` before commit;
- stage only intentional files;
- do not commit staging/import archives or unrelated machine state;
- commit only after task verification;
- push and create/update PR when remote permissions allow;
- review exact PR head, not an outdated commit;
- merge only after required checks/review pass;
- checkout/pull main after merge and re-run the required main verification;
- only then mark MAIN VERIFIED.

If push/PR/merge is blocked by permissions or external service failure, record the exact blocker; do not fabricate completion.

---

## 12. Review law

Review must check more than happy-path tests:
- authority/ownership leakage;
- persistence/migration impact;
- concurrency/CAS/transaction boundaries;
- recovery/idempotency;
- stale-result handling;
- security/credential boundaries;
- backward compatibility;
- test adequacy and false-positive PASS risk.

A self-review does not replace an explicitly required independent review.

---

## 13. Continuous-loop law

After a task is MAIN VERIFIED:
1. update evidence/state/handoff/queue;
2. compute dependency-ready tasks;
3. automatically claim the next valid task;
4. continue the lifecycle.

Do not stop merely to ask for “continue” when the next action is already authorized and unambiguous.

Stop only for:
- a real safety/legal boundary;
- missing external authority that cannot be derived;
- an explicit user stop/pause;
- a hard external blocker that prevents further valid work.

---

## 14. No-false-DONE law

The following are not equivalent:

```text
DESIGNED
≠ CODED
≠ TESTED
≠ BUILT
≠ PACKAGED
≠ LIVE-PROVEN
≠ MERGED
≠ MAIN VERIFIED
≠ PRODUCTION READY
```

Each status must be named accurately.

---

## 15. Project-specific precedence

Order of authority:
1. explicit current user instruction;
2. applicable safety/security constraints;
3. generated or repository-specific `AGENTS.md` rules;
4. frozen accepted architecture/ADR/Master authority;
5. this global execution law;
6. current handoff/state/task queue;
7. historical/reference material.

Lower layers may not silently override higher-authority decisions.

---

## 16. Current FlowKit-Studio-Upgrade freeze rule

The frozen implementation-design Master is identified by its freeze manifest under:

`docs/design/canonical/MASTER_AI_FILM_STUDIO_IMPLEMENTATION_BASELINE_V1_FREEZE_MANIFEST.md`

Implementation tasks must verify that baseline before proceeding.

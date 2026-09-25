# L6_EVIDENCE_GATE_BOARD_V0_12.md
# L6 Evidence Gate Board

**Current maturity:** L5.5 — Reviewed + Partial Hardening Evidence  
**Rule:** a READY harness is not equivalent to executed evidence.

---

| Gate | Architecture | Local Simulation / Harness | Target / Live Evidence | L6 Status |
|---|---|---|---|---|
| Persistence / SQLite | REVIEWED | sandbox WAL/concurrency/crash PASS; Windows harness READY | target Windows execution OPEN | OPEN |
| Provider ambiguity | REVIEWED | FlowKit audit + 1,500 mock recovery runs PASS; live harness READY | shipping-provider fault injection OPEN | OPEN |
| Credential broker | REVIEWED | local security simulation PASS; Electron harness syntax-valid/READY | packaged Windows Electron execution OPEN | OPEN |
| Static QA policy | REVIEWED | severity-policy synthetic spike PASS; analyzer READY | 240-image real calibration OPEN | OPEN |
| Targeted Repair planner | REVIEWED | planner/invalidation synthetic spike PASS; analyzer READY | 90-case real-generation benchmark OPEN | OPEN |
| Scheduler / performance | REVIEWED | 300-shot metadata/scheduler simulation PASS | target Windows/media/provider benchmark OPEN | OPEN |
| Provider profiles | REVIEWED | JSON Schema/profile validation PASS | live account quota/cost refresh for shipping surfaces OPEN | OPEN |
| Contracts / traceability | REVIEWED | schema + ID coverage validation PASS | implementation tests later | NO L6 BLOCKER BY ITSELF |
| Cross-document consistency | REVIEWED | consistency scan PASS | repeat before freeze | NO L6 BLOCKER BY ITSELF |

---

# Gate Closure Rule

A critical runtime gate closes only when all are true:

```text
architecture defined
+ reproducible harness/protocol
+ target/live execution
+ evidence artifact
+ independent review
+ residual risk recorded
```

A local synthetic simulation can strengthen design but cannot substitute for:
- real Windows/Electron behavior;
- real provider billing/remote-side effects;
- real image QA;
- real generation repair behavior.

---

# Current Remaining External Evidence

```text
1. Windows SQLite/migration/backup execution.
2. Windows Electron safeStorage ↔ utilityProcess execution.
3. Live provider response-loss/crash ambiguity proof.
4. 240-image labeled Static QA calibration.
5. 90-case real-generation Targeted Repair benchmark.
6. Shipping-provider live quota/rate-limit/cost observations.
```

Until these are materially closed:

```text
L6 HARDENED = NO
L7 FROZEN = NO
```

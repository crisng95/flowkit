# LIVE_PROOF_EXECUTION_PLAN_V0_12.md
# Target / Live Proof Execution Plan

**Purpose:** remove ambiguity about what must be run on the user's real target environment.

---

# A. Windows Persistence / Update

Run:

```powershell
cd tools\design-spikes\windows-persistence-update
Set-ExecutionPolicy -Scope Process Bypass
.\run-windows-spike.ps1
```

Collect:
- JSON result;
- Windows version;
- filesystem type;
- Python/SQLite versions;
- elapsed/latency;
- migration recovery;
- backup integrity.

Do not run against real production project files.

---

# B. Electron Credential Broker

Run:

```powershell
cd tools\design-spikes\electron-credential-broker
npm install
npm start
type electron_credential_broker_results.json
```

Record:
- Electron version;
- Windows user context;
- `safeStorage.isEncryptionAvailable`;
- round-trip result;
- renderer denial;
- Utility lease result;
- Utility crash/session revocation;
- plaintext canary scans.

Then repeat after app restart.

Before L6, perform a packaged-build run as well; development Electron alone is not the final distribution context.

---

# C. Live Provider Ambiguity

Use only:
- authorized test account/project;
- low-cost test generation;
- no customer data.

Implement provider adapter against:

`tools/design-spikes/live-provider-ambiguity/LIVE_PROVIDER_ADAPTER_CONTRACT.md`

Run at least:

```text
FAIL_BEFORE_TRANSPORT
DROP_RESPONSE_AFTER_DISPATCH
CRASH_AFTER_HANDLE_BEFORE_LOCAL_COMMIT
```

Capture:
- local submission key;
- provider surface/model;
- remote task/operation ID if recovered;
- remote job listing;
- billing/credit observation;
- proof that no blind second submit occurred.

If provider does not expose deterministic reconciliation:
- gate result can legitimately be `AMBIGUOUS_HOLD`;
- do not force a second paid generation merely to make the test "pass."

---

# D. Static QA Calibration

Prepare 240-image labeled set per:
`REAL_IMAGE_STATIC_QA_CALIBRATION_PROTOCOL_V0_9.md`

After the evaluator produces predictions, run:

```powershell
python tools\design-spikes\static-qa-calibration\analyze_static_qa_calibration.py `
  --manifest .\dataset_predictions.jsonl `
  --out .\qa_calibration_report.json
```

Primary gate:
```text
BLOCKING false-negative rate
```

Do not tune repeatedly on locked holdout.

---

# E. Targeted Repair Benchmark

Prepare paired real-generation outcomes per:
`REAL_GENERATION_TARGETED_REPAIR_BENCHMARK_PROTOCOL_V0_9.md`

Analyze:

```powershell
python tools\design-spikes\targeted-repair-benchmark\analyze_repair_benchmark.py `
  --results .\real_results.jsonl `
  --out .\repair_benchmark_report.json
```

A benchmark is valid even if it proves Targeted Repair is worse for some defect classes. The purpose is routing evidence, not defending the architecture.

---

# F. Evidence Naming

Each target execution must create:

```text
EVIDENCE_<gate>_<provider-or-platform>_<YYYYMMDD>.json
EVIDENCE_<gate>_<provider-or-platform>_<YYYYMMDD>.md
```

The Markdown file states:
- environment;
- exact version;
- command;
- result;
- limitations;
- reviewer decision.

No screenshot-only proof.

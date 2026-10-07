# Evidence Ledger Verifier

Purpose: make evidence claims tamper-evident and prevent `HARNESS READY` from being confused with `GATE CLOSED`.

Run:

```powershell
python verify_evidence.py `
  --root ..\..\..\ `
  --ledger ..\..\..\docs\design\EVIDENCE_LEDGER_V0_13.json `
  --rules ..\..\..\docs\design\L6_GATE_RULES_V0_13.json `
  --out .\evidence_gate_report.json
```

When new target/live evidence arrives:
1. store the evidence file;
2. add a ledger entry with SHA-256, class, claims and limitations;
3. run verifier;
4. independent-review the result;
5. only then update gate status.

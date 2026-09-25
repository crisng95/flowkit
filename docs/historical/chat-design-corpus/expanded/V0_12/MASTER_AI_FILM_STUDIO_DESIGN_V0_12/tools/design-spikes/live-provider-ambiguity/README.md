# Live Provider Ambiguity Harness

This harness is intentionally provider-neutral.

It will **not** fake a live proof. A shipping provider adapter must implement the contract and a real test account must be used.

Run:

```powershell
python run_live_provider_ambiguity.py `
  --adapter .\adapter_<provider>.py `
  --fault DROP_RESPONSE_AFTER_DISPATCH `
  --out .\results_<provider>.json
```

Gate closes only when:
- a real request was dispatched;
- the response-loss/crash point is evidenced;
- reconciliation was attempted;
- no blind second submit occurred;
- remote-job/billing evidence is captured;
- the exact provider surface/model/profile is recorded.

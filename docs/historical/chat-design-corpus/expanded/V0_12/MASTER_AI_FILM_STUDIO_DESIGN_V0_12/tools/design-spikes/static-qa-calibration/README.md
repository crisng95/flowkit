# Static QA Calibration Analyzer

Input JSONL row:

```json
{
  "fixture_id": "F001",
  "classes": ["IDENTITY_DRIFT"],
  "predicted_classes": ["IDENTITY_DRIFT"],
  "blocking_classes": ["IDENTITY_DRIFT"],
  "dataset_version": "qa-v1",
  "reviewer_version": "reviewer-v1"
}
```

Run:

```powershell
python analyze_static_qa_calibration.py --manifest .\dataset_predictions.jsonl --out .\qa_calibration_report.json
```

This analyzer measures the evaluator. It does not create labels or inspect images itself.

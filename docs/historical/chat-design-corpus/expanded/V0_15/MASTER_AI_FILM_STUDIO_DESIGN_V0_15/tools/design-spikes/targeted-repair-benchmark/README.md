# Targeted Repair Benchmark Analyzer

Input is paired targeted-repair vs full-regenerate result JSONL.

Run:

```powershell
python analyze_repair_benchmark.py --results .\real_results.jsonl --out .\repair_benchmark_report.json
```

The analyzer computes acceptance, regression, calls, cost and latency by failure class.

It does not generate media itself and therefore cannot be used as repair-efficacy evidence until real paired results are supplied.

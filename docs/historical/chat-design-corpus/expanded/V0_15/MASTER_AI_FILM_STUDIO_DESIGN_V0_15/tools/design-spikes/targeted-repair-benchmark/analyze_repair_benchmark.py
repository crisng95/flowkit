import argparse,json,statistics
from pathlib import Path
from collections import defaultdict

parser=argparse.ArgumentParser()
parser.add_argument("--results",required=True,help="JSONL paired targeted/full-regenerate outcomes")
parser.add_argument("--out",default="repair_benchmark_report.json")
args=parser.parse_args()

rows=[json.loads(x) for x in Path(args.results).read_text(encoding="utf-8").splitlines() if x.strip()]
by=defaultdict(list)
for r in rows: by[r["failure_code"]].append(r)

def summarize(group,arm):
    xs=[r[arm] for r in group]
    accepted=[x for x in xs if x["accepted"]]
    return {
      "n":len(xs),
      "acceptance_rate":sum(x["accepted"] for x in xs)/len(xs) if xs else None,
      "blocking_regression_rate":sum(x.get("new_blocking_regression",False) for x in xs)/len(xs) if xs else None,
      "high_regression_rate":sum(x.get("new_high_regression",False) for x in xs)/len(xs) if xs else None,
      "avg_provider_calls":statistics.mean(x["provider_calls"] for x in xs) if xs else None,
      "avg_cost":statistics.mean(x["cost"] for x in xs) if xs else None,
      "avg_latency_s":statistics.mean(x["latency_s"] for x in xs) if xs else None,
      "avg_cost_per_accepted":(sum(x["cost"] for x in xs)/len(accepted)) if accepted else None,
    }

report={"overall":{},"by_failure_code":{}}
report["overall"]["targeted"]=summarize(rows,"targeted")
report["overall"]["full_regen"]=summarize(rows,"full_regen")
for code,group in sorted(by.items()):
    report["by_failure_code"][code]={
      "targeted":summarize(group,"targeted"),
      "full_regen":summarize(group,"full_regen")
    }

Path(args.out).write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps(report,indent=2))

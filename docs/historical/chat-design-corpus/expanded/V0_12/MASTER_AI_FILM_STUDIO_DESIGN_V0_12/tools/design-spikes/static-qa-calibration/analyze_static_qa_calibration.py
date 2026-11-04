import argparse, json, math
from pathlib import Path
from collections import defaultdict

parser=argparse.ArgumentParser()
parser.add_argument("--manifest",required=True,help="JSONL with ground_truth and prediction")
parser.add_argument("--out",default="qa_calibration_report.json")
args=parser.parse_args()

rows=[]
for line in Path(args.manifest).read_text(encoding="utf-8").splitlines():
    if line.strip(): rows.append(json.loads(line))

stats=defaultdict(lambda: {"tp":0,"fp":0,"tn":0,"fn":0})

for r in rows:
    classes=set(r.get("classes",[])) | set(r.get("predicted_classes",[]))
    for c in classes:
        gt=c in r.get("classes",[])
        pred=c in r.get("predicted_classes",[])
        if gt and pred: stats[c]["tp"]+=1
        elif not gt and pred: stats[c]["fp"]+=1
        elif gt and not pred: stats[c]["fn"]+=1
        else: stats[c]["tn"]+=1

def div(a,b): return a/b if b else None

metrics={}
for c,s in sorted(stats.items()):
    precision=div(s["tp"],s["tp"]+s["fp"])
    recall=div(s["tp"],s["tp"]+s["fn"])
    specificity=div(s["tn"],s["tn"]+s["fp"])
    f1=div(2*precision*recall,precision+recall) if precision is not None and recall is not None and (precision+recall) else None
    metrics[c]={**s,"precision":precision,"recall":recall,"specificity":specificity,"f1":f1,
                "false_negative_rate":div(s["fn"],s["tp"]+s["fn"])}

blocking=set(r.get("blocking_classes",[]) for r in [])
blocking_classes=sorted({c for r in rows for c in r.get("blocking_classes",[])})
blocking_fn=sum(metrics.get(c,{}).get("fn",0) for c in blocking_classes)
blocking_pos=sum(metrics.get(c,{}).get("tp",0)+metrics.get(c,{}).get("fn",0) for c in blocking_classes)

report={
  "fixtures":len(rows),
  "classes":metrics,
  "blocking_classes":blocking_classes,
  "blocking_false_negative_rate":div(blocking_fn,blocking_pos),
  "dataset_versions":sorted({r.get("dataset_version") for r in rows if r.get("dataset_version")}),
  "reviewer_versions":sorted({r.get("reviewer_version") for r in rows if r.get("reviewer_version")}),
}
Path(args.out).write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps(report,indent=2))

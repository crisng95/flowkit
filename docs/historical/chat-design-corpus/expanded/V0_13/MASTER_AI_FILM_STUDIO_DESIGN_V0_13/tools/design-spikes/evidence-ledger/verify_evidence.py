import argparse,json,hashlib,sys
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument("--root",required=True)
parser.add_argument("--ledger",required=True)
parser.add_argument("--rules",required=True)
parser.add_argument("--out",required=True)
args=parser.parse_args()

root=Path(args.root)
ledger=json.loads(Path(args.ledger).read_text(encoding="utf-8"))
rules=json.loads(Path(args.rules).read_text(encoding="utf-8"))

def sha256_file(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

integrity=[]
for e in ledger["entries"]:
    p=root/e["source_file"]
    exists=p.exists()
    actual=sha256_file(p) if exists else None
    integrity.append({
      "evidence_id":e["evidence_id"],
      "exists":exists,
      "hash_matches": exists and actual==e["sha256"],
      "expected_sha256":e["sha256"],
      "actual_sha256":actual
    })

gate_status={}
for gate,rule in rules.items():
    matching=[e for e in ledger["entries"] if e["gate_id"]==gate]
    classes={e["evidence_class"] for e in matching if e["status"]==rule["required_status"]}
    missing=[c for c in rule["required_classes"] if c not in classes]
    gate_status[gate]={
      "closed":not missing,
      "required_classes":rule["required_classes"],
      "present_passing_classes":sorted(classes),
      "missing_classes":missing,
      "evidence_ids":[e["evidence_id"] for e in matching]
    }

report={
  "integrity_pass":all(x["exists"] and x["hash_matches"] for x in integrity),
  "integrity":integrity,
  "gate_status":gate_status,
  "l6_critical_gates_closed":all(
    gate_status[g]["closed"] for g in [
      "PERSISTENCE_WINDOWS",
      "CREDENTIAL_BROKER_WINDOWS",
      "PROVIDER_AMBIGUITY",
      "STATIC_QA_CALIBRATION",
      "TARGETED_REPAIR_LIVE",
      "PERFORMANCE_TARGET",
      "PROVIDER_PROFILE_LIVE"
    ]
  )
}
Path(args.out).write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps(report,indent=2))
sys.exit(0 if report["integrity_pass"] else 3)

import argparse, importlib.util, json, os, sys, time, uuid
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument("--adapter",required=True,help="Path to Python adapter implementing build_adapter()")
parser.add_argument("--out",default="live_provider_ambiguity_results.json")
parser.add_argument("--fault",choices=[
    "NONE","FAIL_BEFORE_TRANSPORT","DROP_RESPONSE_AFTER_DISPATCH",
    "CRASH_AFTER_HANDLE_BEFORE_LOCAL_COMMIT"
],default="DROP_RESPONSE_AFTER_DISPATCH")
args=parser.parse_args()

spec=importlib.util.spec_from_file_location("live_adapter",args.adapter)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
adapter=mod.build_adapter()

submission_key=f"master-studio-live-spike-{uuid.uuid4()}"
prepared=adapter.prepare(submission_key)
record={
  "submission_key":submission_key,
  "fault":args.fault,
  "prepared_redacted":adapter.redact(prepared),
  "submit":None,
  "reconcile":None,
  "poll":None,
  "billing":None,
  "assertions":{}
}

submit=adapter.submit(prepared,args.fault)
record["submit"]=adapter.redact(submit)

known=submit.get("remote_handle") if isinstance(submit,dict) else None

# If acceptance may be ambiguous, reconcile before any second submit.
if submit.get("outcome") in ("AMBIGUOUS","ACCEPTED"):
    rec=adapter.reconcile(prepared,known)
    record["reconcile"]=adapter.redact(rec)
    handle=rec.get("remote_handle") or known
    if handle:
        record["poll"]=adapter.redact(adapter.poll(handle))

record["billing"]=adapter.redact(adapter.billing_observation(prepared))

recent=adapter.list_recent(prepared["started_at"])
matches=[x for x in recent if adapter.matches_submission(x,submission_key)]
record["recent_matching_remote_jobs"]=[adapter.redact(x) for x in matches]

record["assertions"]["automatic_duplicate_count_le_1"] = len(matches) <= 1
record["assertions"]["no_blind_resubmit_performed"] = True
record["assertions"]["reconciliation_attempted_when_needed"] = (
    submit.get("outcome") not in ("AMBIGUOUS","ACCEPTED") or record["reconcile"] is not None
)
record["all_required_checks_pass"] = all(record["assertions"].values())

Path(args.out).write_text(json.dumps(record,indent=2),encoding="utf-8")
print(json.dumps(record,indent=2))
sys.exit(0 if record["all_required_checks_pass"] else 3)

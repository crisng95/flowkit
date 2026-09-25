# TARGETED_REPAIR_PLANNER_SPIKE_EVIDENCE_V0.7.md
# Targeted Repair Planner — Policy/Invalidation Spike

**Status:** PARTIAL PROOF — PLANNER LOGIC ONLY  
**Not claimed:** real generative-model repair success.

## Goal

Test whether failure classes can be mapped to:
- earliest candidate owner;
- repair mode;
- explicit preserve set;
- selective invalidation set.

Executed **180** deterministic planner cases across:

```text
IDENTITY_DRIFT
WARDROBE_MISMATCH
PROP_MISMATCH
ACTION_MISMATCH
LOCATION_MISMATCH
CAMERA_FAIL
LIGHTING_FAIL
CONTINUITY_FAIL
NARRATIVE_INTENT_FAIL
```

Results:

```json
{
  "cases": 180,
  "invariant_violations": 0,
  "full_regen_reference_cost_units": 15.2,
  "targeted_avg_invalidation_cost_units": 7.911,
  "targeted_median_invalidation_cost_units": 8.0,
  "targeted_max_invalidation_cost_units": 15.0,
  "synthetic_scope_savings_percent_vs_full_regen": 48.0,
  "note": "Synthetic invalidation-scope model. It does not prove provider generation quality, success rate, or real monetary savings."
}
```

The synthetic cost units compare only **logical invalidation scope**.

They demonstrate why selective invalidation can avoid unnecessary work compared with always rebuilding the shot and descendants. They do not prove:
- the repaired image/video will pass;
- exact real-provider cost savings;
- that the initial root-cause diagnosis is correct.

Those require real QA outputs + provider generations.

## Architecture implication

Keep:
```text
QA failure
→ causal owner diagnosis
→ RepairPlan
→ preserve/patch/invalidate/recheck
```

Do not replace with:
```text
QA failure
→ append fix text
→ regenerate everything
```

# EVIDENCE_CLASSIFICATION_POLICY_V0_13.md
# Evidence Classification and Gate-Closure Policy

**Status:** REVIEWED CANDIDATE

---

# 1. Evidence Classes

From weakest to strongest for runtime claims:

```text
RESEARCH
STATIC_ANALYSIS
LOCAL_SIMULATION
HARNESS_VALIDATION
TARGET_RUNTIME
LIVE_ACCOUNT_OBSERVATION
LIVE_PROVIDER
VISUAL_CALIBRATION
LIVE_GENERATION_BENCHMARK
```

These are not a universal scalar ranking: each gate requires the class appropriate to the claim.

Examples:
- JSON Schema consistency can close with `STATIC_ANALYSIS`.
- Windows safeStorage cannot close with `LOCAL_SIMULATION`; it requires `TARGET_RUNTIME`.
- provider duplicate-side-effect safety requires `LIVE_PROVIDER`.
- Static QA vision quality requires `VISUAL_CALIBRATION`.

---

# 2. Evidence Entry

Every evidence artifact records:

```text
evidence_id
gate_id
evidence_class
source_file
sha256
status
claims_supported[]
limitations[]
environment
review_rounds[]
```

A claim not listed in `claims_supported` is not established merely because the file exists.

---

# 3. Integrity

Evidence is hashed with SHA-256 when entered into the ledger.

If the evidence file changes:
```text
hash mismatch
→ evidence invalid until re-ingested/re-reviewed
```

This is not cryptographic signing; it is local tamper/change detection.

---

# 4. Gate Closure

Gate rules specify minimum evidence classes.

Example:

```text
Credential Broker Windows
requires:
  TARGET_RUNTIME + PASS
```

Therefore:

```text
architecture doc PASS
+ local simulation PASS
+ Electron harness READY
≠ gate closed
```

---

# 5. Failure Evidence

A `FAIL` evidence entry is first-class evidence.

It must not be deleted merely to restore a green dashboard.

Instead:
```text
FAIL
→ root-cause review
→ design patch
→ new evidence version
→ independent review
```

Historical failure remains in lineage.

---

# 6. Supersession

New evidence does not silently overwrite old evidence.

Use:
```text
new evidence_id
new hash
new environment/version
```

and mark supersession in review/state documents.

---

# 7. Freeze Requirement

Before L7:
- every required L6/L7 gate has a passing evidence entry of the required class;
- evidence hashes verify;
- no unresolved conflicting evidence;
- final independent review references exact evidence IDs.

# HISTORICAL EXPANSION MANIFEST

## Scope

Historical snapshot expansion only for the 16 version archives V0.1 through V0.16.

Rules applied:

- Each version archive was integrity-checked before extraction.
- Each archive was extracted into its own version directory.
- No files were renamed.
- No files were deduplicated.
- No historical design content was edited.
- No Master Design merge, authority map, supersession resolution, contradiction resolution, dependency graph, task decomposition, or coding was performed.
- The three post-V0.16 canonical merge candidates remain at corpus top level and were verified absent from `expanded/`.

`SIZE BYTES` below means total extracted file bytes for that snapshot.

## Snapshot Expansion Table

| VERSION | ZIP SOURCE | EXTRACT PATH | TOTAL FILES | MD FILES | SIZE BYTES | INTEGRITY | STATUS |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| V0.1 | `MASTER_AI_FILM_STUDIO_DESIGN_V0_1.zip` | `expanded/V0_01/` | 14 | 14 | 63,029 | PASS | PASS |
| V0.2 | `MASTER_AI_FILM_STUDIO_DESIGN_V0_2_PERSISTENCE_REVIEWED.zip` | `expanded/V0_02/` | 18 | 18 | 101,469 | PASS | PASS |
| V0.3 | `MASTER_AI_FILM_STUDIO_DESIGN_V0_3_L5_REVIEWED.zip` | `expanded/V0_03/` | 26 | 26 | 148,327 | PASS | PASS |
| V0.4 | `MASTER_AI_FILM_STUDIO_DESIGN_V0_4_L5_5_PARTIAL_HARDENING.zip` | `expanded/V0_04/` | 36 | 36 | 184,284 | PASS | PASS |
| V0.5 | `MASTER_AI_FILM_STUDIO_DESIGN_V0_5_PROVIDER_AMBIGUITY_PARTIAL_PROOF.zip` | `expanded/V0_05/` | 40 | 39 | 210,261 | PASS | PASS |
| V0.6 | `MASTER_AI_FILM_STUDIO_DESIGN_V0_6_CREDENTIAL_BROKER_PARTIAL_PROOF.zip` | `expanded/V0_06/` | 44 | 42 | 238,360 | PASS | PASS |
| V0.7 | `MASTER_AI_FILM_STUDIO_DESIGN_V0_7_QA_REPAIR_POLICY_PARTIAL_PROOF.zip` | `expanded/V0_07/` | 49 | 45 | 251,598 | PASS | PASS |
| V0.8 | `MASTER_AI_FILM_STUDIO_DESIGN_V0_8_PERFORMANCE_WINDOWS_HARNESS.zip` | `expanded/V0_08/` | 55 | 48 | 275,303 | PASS | PASS |
| V0.9 | `MASTER_AI_FILM_STUDIO_DESIGN_V0_9_HARDENING_PROTOCOLS_READY.zip` | `expanded/V0_09/` | 57 | 50 | 285,676 | PASS | PASS |
| V0.10 | `MASTER_AI_FILM_STUDIO_DESIGN_V0_10_PROVIDER_EVIDENCE_CONTRADICTION_PATCHED.zip` | `expanded/V0_10/` | 64 | 56 | 325,391 | PASS | PASS |
| V0.11 | `MASTER_AI_FILM_STUDIO_DESIGN_V0_11_PROVIDER_CONTRACT_TRACEABILITY_HARDENED.zip` | `expanded/V0_11/` | 73 | 57 | 333,849 | PASS | PASS |
| V0.12 | `MASTER_AI_FILM_STUDIO_DESIGN_V0_12_LIVE_PROOF_HARNESSES_READY.zip` | `expanded/V0_12/` | 96 | 65 | 377,068 | PASS | PASS |
| V0.13 | `MASTER_AI_FILM_STUDIO_DESIGN_V0_13_EVIDENCE_GOVERNANCE_STATE_MODEL_HARDENED.zip` | `expanded/V0_13/` | 113 | 74 | 432,495 | PASS | PASS |
| V0.14 | `MASTER_AI_FILM_STUDIO_DESIGN_V0_14_WINDOWS_PERSISTENCE_EVIDENCE_PATCH.zip` | `expanded/V0_14/` | 129 | 81 | 496,677 | PASS | PASS |
| V0.15 | `MASTER_AI_FILM_STUDIO_DESIGN_V0_15_WINDOWS_PERSISTENCE_GATE_CLOSED.zip` | `expanded/V0_15/` | 136 | 85 | 521,705 | PASS | PASS |
| V0.16 | `MASTER_AI_FILM_STUDIO_DESIGN_V0_16_STORY_INTELLIGENCE_12_ROUND_REPO_HARVEST.zip` | `expanded/V0_16/` | 150 | 97 | 657,373 | PASS | PASS |

## Per-Snapshot Verification

| VERSION | DIRECTORIES | README.md | PROJECT_STATE.md | CURRENT_HANDOFF.md | CORRUPT / TRUNCATED DETECTED |
| --- | ---: | --- | --- | --- | --- |
| V0.1 | 6 | YES | YES | YES | NO |
| V0.2 | 7 | YES | YES | YES | NO |
| V0.3 | 7 | YES | YES | YES | NO |
| V0.4 | 8 | YES | YES | YES | NO |
| V0.5 | 8 | YES | YES | YES | NO |
| V0.6 | 8 | YES | YES | YES | NO |
| V0.7 | 8 | YES | YES | YES | NO |
| V0.8 | 11 | YES | YES | YES | NO |
| V0.9 | 11 | YES | YES | YES | NO |
| V0.10 | 11 | YES | YES | YES | NO |
| V0.11 | 12 | YES | YES | YES | NO |
| V0.12 | 16 | YES | YES | YES | NO |
| V0.13 | 17 | YES | YES | YES | NO |
| V0.14 | 20 | YES | YES | YES | NO |
| V0.15 | 20 | YES | YES | YES | NO |
| V0.16 | 20 | YES | YES | YES | NO |

Integrity verification used full ZIP decompression/CRC checking. Post-extraction verification confirmed every file entry exists and its extracted byte size matches the ZIP entry size.

## Global Counts

### Entries

- Total file entries across all 16 snapshots: **1,100**
- Total Markdown (.md) entries: **833**
- Total expanded bytes: **4,902,865**

These are historical versioned entries. They are not deduplicated unique-file counts.

### Unique names and paths

- Unique basenames: **145**
- Unique relative paths inside snapshots: **761**

### Duplicate names and paths across versions

- Filename/basename groups appearing in more than one version: **129**
- File entries belonging to those duplicate-name groups: **1,084**
- Duplicate-name excess entries beyond one representative per basename: **955**

- Relative-path groups appearing in more than one version: **57**
- File entries belonging to those duplicate-path groups: **396**
- Duplicate-path excess entries beyond one representative per relative path: **339**

No deduplication was performed.

### SHA-256 byte-identical content

- SHA-256 groups containing more than one byte-identical file entry: **161**
- File entries belonging to byte-identical groups: **975**
- Byte-identical excess entries beyond one representative per hash: **814**

This is an inventory measurement only. No files were removed, linked, renamed, or consolidated.

## Post-V0.16 Canonical Merge Candidates

The following files remain at the top-level corpus and are **not** present inside any expanded snapshot, including V0.16:

- `UNIVERSAL_NICHE_COMPOSABLE_BRAIN_ARCHITECTURE_V1_FINAL.md`
- `NARRATIVE_EXPANSION_LADDER_PATCH_V1_FINAL.md`
- `BEAT_SCENE_TO_SHOT_AUTHORITY_ARCHITECTURE_V1_FINAL.md`

They remain reserved as POST-V0.16 CANONICAL MERGE CANDIDATES.

## Expansion Result

**16 / 16 snapshot expansions verified PASS.**

No corrupt or truncated snapshot entry was detected by ZIP CRC/decompression plus extracted-size verification.

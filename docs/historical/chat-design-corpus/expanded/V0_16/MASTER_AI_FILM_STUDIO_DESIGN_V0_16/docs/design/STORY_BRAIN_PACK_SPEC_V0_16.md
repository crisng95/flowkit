# STORY_BRAIN_PACK_SPEC_V0_16.md
# Dynamic Story Brain Pack Specification V0.16

**Status:** REVIEWED CANDIDATE.  
**Purpose:** allow the same core engine to behave appropriately across domains/genres/formats without forking Story code.

---

# 1. Brain Pack types

```text
DOMAIN      e.g. family drama, true crime, history, science, business
GENRE       e.g. horror, romance, thriller, comedy, documentary
AUDIENCE    e.g. children, general adult, specialist, local cultural audience
FORMAT      e.g. 60s short, 10-min YouTube, 20-min documentary, feature screenplay
PLATFORM    e.g. YouTube retention-aware, vertical short-form
CRAFT       e.g. Truby-inspired, Story Spine, mystery reveal strategy
POLICY      project/company constraints
```

Packs are composable. No pack is the entire Brain.

---

# 2. Pack schema

```yaml
BrainPack:
  id: string
  version: semver
  type: DOMAIN|GENRE|AUDIENCE|FORMAT|PLATFORM|CRAFT|POLICY
  name: string
  description: string
  provenance:
    source: string
    license: string
    adapted_from: []
  applies_when:
    project_tags: []
    excludes: []
  hard_constraints: []
  research:
    required_dimensions: []
    preferred_source_types: []
    risk_flags: []
  premise:
    questions: []
    anti_patterns: []
  angle:
    lenses: []
    novelty_checks: []
  theme:
    prompts_or_rubrics: []
  character:
    required_fields: []
    archetype_policy: advisory_only
    voice_guidance: []
  conflict:
    escalation_patterns: []
    forbidden_shortcuts: []
  structure:
    candidate_strategies: []
    required_turns: []
    optional_turns: []
  emotion:
    arc_patterns: []
    rhythm_guidance: []
  scene:
    required_checks: []
    patterns: []
  dialogue:
    rubrics: []
    anti_patterns: []
  pacing:
    target_ranges: {}
  qa:
    enabled_critics: []
    severity_overrides: {}
    acceptance_overrides: {}
  examples: []
```

---

# 3. Hard vs advisory policy

Brain Pack guidance is divided into:

```text
HARD CONSTRAINT
must be followed because of format, factual domain, safety, explicit project lock, etc.

ADVISORY CRAFT POLICY
can be ignored when story evidence justifies a stronger choice.
```

Example:

```text
FORMAT: 60-second vertical
hard: total runtime target
advisory: hook in first X seconds

CRAFT: three-act
advisory: turning-point positions
NOT hard law
```

---

# 4. Resolver algorithm

```text
1 collect project tags + explicit selections
2 load eligible packs
3 reject incompatible versions/licenses
4 select relevant pack sections per stage
5 resolve policy conflicts by precedence
6 emit BrainResolution
7 cache by project + pack version fingerprint
8 invalidate only stages affected by changed pack sections
```

## Precedence

```text
explicit locked project/user constraints
>
format hard limits
>
domain factual constraints
>
company/project policy
>
selected craft methodology
>
genre/audience/platform advisory guidance
```

---

# 5. Stage-scoped context

Do not concatenate every Brain Pack into every prompt.

```text
Premise stage → premise + domain/format relevant slices
Research stage → research slices
Character stage → character slices
Dialogue stage → dialogue/voice slices
Critique stage → critic rubrics
```

This prevents prompt bloat and policy collisions.

---

# 6. Versioning and reproducibility

Every generated creative decision records:
- `BrainResolution.id`;
- pack IDs/versions;
- selected sections;
- project overrides;
- compiler/model version used for that stage.

Changing a Brain Pack later does not silently rewrite locked projects.

---

# 7. Donor content rule

Licensed methodology repos may be adapted as Brain Pack content. Unlicensed/GPL sources may inform independently authored packs but their source text/code is not copied by default.

The Pack Registry stores provenance and license metadata so future commercial packaging can audit what shipped.

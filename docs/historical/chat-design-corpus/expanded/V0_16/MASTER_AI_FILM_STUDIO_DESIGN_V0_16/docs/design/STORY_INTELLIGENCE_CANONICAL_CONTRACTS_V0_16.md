# STORY_INTELLIGENCE_CANONICAL_CONTRACTS_V0_16.md
# Story Intelligence Canonical Contracts V0.16

**Status:** REVIEWED CANDIDATE.  
**Goal:** structured, provider/model-neutral contracts. Prompt prose is a compiled/rendered view, not canonical state.

---

# 1. Contract rules

Every persisted creative contract should carry at minimum:

```text
id
project_id
version
status: DRAFT | REVIEW | APPROVED | LOCKED | SUPERSEDED
created_at / updated_at
created_by / provenance
source_version_ids[]
revision_reason
```

Persistent/public contracts must remain JSON-serializable. Shape validation and semantic validation are separate.

---

# 2. StorySeed

```yaml
StorySeed:
  source_type: idea|topic|outline|screenplay|research|project
  raw_intent: string
  audience_intent: string?
  format_target: string?
  duration_target: string?
  explicit_constraints: []
  source_refs: []
```

---

# 3. PremiseCandidate

```yaml
PremiseCandidate:
  id: string
  protagonist_or_focal_subject: string
  situation: string
  disruptive_force: string
  dramatic_problem: string
  objective_or_question: string
  opposition: string
  stakes: string
  contradiction_or_irony: string?
  transformation_potential: string?
  specificity_hooks: []
  research_dependencies: []
  candidate_risks: []
  critique_status: string
```

---

# 4. AngleCandidate

```yaml
AngleCandidate:
  id: string
  lens: string
  focal_access: string
  central_question: string
  information_advantage: string
  emotional_access: string
  research_potential: string
  visual_potential: string
  novelty_basis: string
  audience_fit: string
  format_fit: string
  risks: []
```

---

# 5. ThemeHypothesis

```yaml
ThemeHypothesis:
  thematic_question: string
  value_a: string
  value_b: string
  working_argument: string
  counter_argument: string
  protagonist_initial_belief: string?
  story_tests: []
  final_position: string?
  ambiguity_allowed: bool
  anti_didacticism_constraints: []
```

---

# 6. ResearchBrief

```yaml
ResearchBrief:
  mode: NONE|LIGHT_CONTEXT|DEEP_FACTUAL|DOCUMENTARY|HISTORICAL|TECHNICAL|CULTURAL|MARKET_AUDIENCE
  questions:
    - id: string
      question: string
      research_goal: string
      priority: BLOCKING|HIGH|MEDIUM|LOW
      perspective: string?
  source_requirements: []
  freshness_requirements: []
  excluded_sources: []
  max_budget: object?
  stop_policy: object
```

---

# 7. EvidenceClaim

```yaml
EvidenceClaim:
  id: string
  proposition: string
  source_id: string
  source_url_or_ref: string
  source_date: string?
  source_type: string
  quote_or_locator: string?
  support_level: string
  factual_status: SUPPORTED|CONTESTED|UNRESOLVED|REJECTED|NOT_CHECKED
  domain_tags: []
  scope: string?
  uncertainty: string?
```

`EvidenceEdge`:

```yaml
relationship: SUPPORTS|CONTRADICTS|QUALIFIES|EXTENDS
source_claim_id: string
target_claim_id: string
resolution_status: UNRESOLVED|RESOLVED_SCOPE|RESOLVED_SOURCE|RESOLVED_TARGET|IRREDUCIBLE
```

---

# 8. StoryMaterial

```yaml
StoryMaterial:
  id: string
  evidence_claim_ids: []
  material_type: HUMAN_DETAIL|SETTING_DETAIL|CONFLICT_SOURCE|CHARACTER_PRESSURE|PROP|EVENT|DIALOGUE_SEED|SCENE_OPPORTUNITY|MOTIF
  concrete_detail: string
  dramatic_function: string
  candidate_characters: []
  candidate_story_locations: []
  factual_constraints: []
  uncertainty_constraints: []
```

---

# 9. BrainResolution

```yaml
BrainResolution:
  project_id: string
  resolved_packs:
    - pack_id: string
      version: string
      type: domain|genre|audience|format|platform|craft
      selected_sections: []
      precedence: int
  conflicts:
    - policy_a: string
      policy_b: string
      resolution: string
  effective_constraints: []
  advisory_guidance: []
```

---

# 10. CharacterModelVersion

```yaml
CharacterModelVersion:
  character_id: string
  role: string
  external_want: string?
  internal_need: string?
  fear: string?
  formative_pressure: string?
  mistaken_belief: string?
  values: []
  contradictions: []
  strengths: []
  flaws_or_defenses: []
  secrets: []
  social_mask: string?
  private_self: string?
  preferred_tactics: []
  boundaries: []
  voice_registers:
    - id: string
      trigger: string
      syntax: string
      vocabulary: string
      rhythm: string
  arc_hypothesis: object?
```

---

# 11. CharacterKnowledgeState

```yaml
CharacterKnowledgeState:
  character_id: string
  story_time: string
  knows: []
  believes: []
  suspects: []
  misunderstands: []
  hides: []
  evidence_event_ids: []
```

Knowledge state is versioned independently from stable character psychology.

---

# 12. RelationshipState

```yaml
RelationshipState:
  relationship_id: string
  participants: []
  public_relation: string
  private_relation: string
  trust: number?
  power_balance: string
  debts: []
  resentments: []
  dependencies: []
  secrets_between_them: []
  current_pressure: string?
  last_change_event_id: string?
```

Scores such as trust are optional convenience data and cannot replace descriptive state.

---

# 13. ConflictModel

```yaml
ConflictModel:
  central_objective: string
  opposition_forces:
    - id: string
      type: external|interpersonal|internal|systemic|environmental|time|resource
      objective: string
      leverage: []
  incompatibilities: []
  escalation_steps: []
  reversals: []
  resolution_conditions: []
```

---

# 14. StakesModel

```yaml
StakesModel:
  immediate: []
  relational_social: []
  identity_value: []
  irreversible: []
  escalation_events: []
  false_or_perceived_stakes: []
```

---

# 15. StoryGraph

```yaml
StoryGraph:
  nodes:
    - id: string
      type: EVENT|DECISION|REVELATION|REVERSAL|SETUP|PAYOFF|STATE_CHANGE
      summary: string
  edges:
    - from: string
      to: string
      type: CAUSES|ENABLES|MOTIVATES|BLOCKS|REVEALS|ESCALATES|PAYS_OFF|CONTRADICTS_EXPECTATION
      rationale: string
```

Major nodes require incoming/outgoing causal rationale unless explicitly marked `ROOT`, `EPILOGUE`, `MONTAGE_ASSOCIATIVE`, etc.

---

# 16. EmotionalArcPlan

```yaml
EmotionalArcPlan:
  subject: character_id|audience
  arc_type: positive|negative|flat_tested|cyclical|unresolved|custom
  initial_state: string
  pressure_points: []
  turns: []
  peak: string?
  resolution: string?
  final_state: string
  thematic_relation: string?
```

---

# 17. EmotionalRhythmPoint

```yaml
EmotionalRhythmPoint:
  story_location_id: string
  tension: number?
  valence: number?
  arousal: number?
  uncertainty: number?
  hope_fear_balance: number?
  release: number?
  rationale: string
```

Numeric signals are advisory estimates and require calibration if used for automated thresholds.

---

# 18. SceneContract

```yaml
SceneContract:
  scene_id: string
  sequence_id: string
  narrative_function: string
  pov_or_focal_relation: string
  start_state_refs: []
  audience_knowledge_in: []
  character_knowledge_refs: []
  objective: string
  opposition: string
  primary_tactic: string?
  escalation: []
  turn: string
  key_change:
    dimensions: [knowledge|power|relationship|goal|risk|emotion|belief|resource|options|status|commitment]
    before: string
    after: string
  emotional_target: string
  tension_target: object?
  setup_obligations: []
  payoff_obligations: []
  end_state_refs: []
  next_causal_edges: []
  static_scene_exception: string?
```

Semantic validation:
- `key_change` required unless `static_scene_exception` has an accepted narrative function;
- `turn` must relate to objective/opposition/key_change;
- knowledge state cannot reveal unsupported knowledge.

---

# 19. BeatContract

```yaml
BeatContract:
  beat_id: string
  scene_id: string
  intention: string
  action_or_tactic: string
  reaction: string
  resistance_or_new_information: string
  micro_change: string
  speaker_or_actor_ids: []
  knowledge_delta: []
  emotional_delta: string?
  relationship_delta: string?
  setup_payoff_refs: []
```

---

# 20. DialogueIntent

```yaml
DialogueIntent:
  exchange_id: string
  beat_id: string
  speaker_id: string
  listener_ids: []
  surface_intent: string
  hidden_intent: string?
  desired_outcome: string
  avoidance: string?
  tactic: string
  pressure_point: string?
  knowledge_constraints: []
  forbidden_disclosures: []
  voice_register_id: string?
  subtext_target: string?
```

The generated line is an artifact derived from `DialogueIntent`, not the intent itself.

---

# 21. SetupPayoffLink

```yaml
SetupPayoffLink:
  id: string
  type: QUESTION|OBJECT|SKILL|PROMISE|RELATIONSHIP|MOTIF|INFORMATION|RULE
  setup_location: string
  promise: string
  audience_visibility: string
  characters_aware: []
  reinforcements: []
  escalations: []
  expected_payoff_window: string?
  payoff_location: string?
  payoff: string?
  consequence: string?
  status: PLANTED|DEVELOPING|PAID|INTENTIONALLY_OPEN|BROKEN
```

---

# 22. CritiqueFinding

```yaml
CritiqueFinding:
  id: string
  critic_type: string
  story_version: string
  location_refs: []
  defect_code: string
  severity: BLOCKING|HIGH|MEDIUM|LOW|COSMETIC
  evidence: []
  explanation: string
  suspected_root_layer: string
  confidence: string
  competing_interpretation: string?
  recommendation: string
```

A bare `PASS` with no performed checks is not strong evidence.

---

# 23. StoryRepairPlan

```yaml
StoryRepairPlan:
  finding_ids: []
  root_cause_layer: string
  repair_mode: PATCH_LOCAL|REWRITE_BEAT|REWRITE_SCENE|REPLAN_SEQUENCE|REWORK_CHARACTER|RESEARCH_MORE|RESTRUCTURE|REOPEN_PREMISE_ANGLE
  preserve_refs: []
  patch_targets: []
  invalidate_refs: []
  required_rechecks: []
  max_attempts: integer
  escalation_rule: string
```

---

# 24. StoryQualityResult

```yaml
StoryQualityResult:
  story_version: string
  verdict: PASS|WARN|FAIL|NOT_EVALUATED
  dimensions: []
  blocking_findings: []
  high_findings: []
  advisory_score: number?
  bottleneck_dimension: string?
  evidence_refs: []
```

`advisory_score` cannot override a blocking finding.

---

# 25. ScriptLockManifest

```yaml
ScriptLockManifest:
  story_version: string
  screenplay_artifact_hash: string
  contract_hashes: []
  unresolved_blocking_count: 0
  unresolved_high_count: integer
  research_evidence_snapshot_id: string?
  critique_snapshot_id: string
  setup_payoff_snapshot_id: string
  timeline_snapshot_id: string
  approved_by: string
  locked_at: string
```

A new upstream StoryVersion creates a new lock candidate; it never mutates a prior lock in place.

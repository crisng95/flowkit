# REFERENCE_PROJECTS.md
# Reference Repository Adoption Matrix — V0.1

This document records what is actually useful from each audited repository. It does not make any repository the master architecture.

---

| Module / Concept | Source | Evidence level | Decision | What to take | What NOT to take | Integration |
|---|---|---:|---|---|---|---|
| Entity persistence / media refs | `crisng95/flowkit` | A/B | KEEP | typed entity persistence, reference media IDs, missing-ref block, resolve refs into generation | scene-centric domain authority | wrap behind canonical Entity/Reference service |
| Parent-image continuity | `crisng95/flowkit` | A/B | KEEP+ADAPT | parent accepted image as base + canonical refs | universal “completely different moment” continuation wording | continuity edge executor |
| Dependency waves / resume | `crisng95/flowkit` | B | KEEP | wave scheduling, skip completed, retry/resume, invalidation | provider-specific domain leakage | orchestration service |
| Flow provider integration | `crisng95/flowkit` | A/B | KEEP AS ADAPTER | image/edit/video/reference transport | make Google Flow canonical domain | `GoogleFlowAdapter` |
| Video review | `crisng95/flowkit` | A | KEEP+EXTEND | ffmpeg/contact-sheet review and dimensions | treat weighted score as final creative truth | Video QA service |
| Cross-stage contracts | `zhangzhangco/film-production-skills` | B | ADAPT | request/result envelopes, IDs, diagnostics, lineage, handoff | treat skills/docs as completed runtime | canonical contract package |
| Screenplay structure | `zhangzhangco/film-production-skills` | B | ADAPT | scene/unit/beat/rhythm structure | fixed implementation coupling | Story/Beat contracts |
| Camera shot plan | `zhangzhangco/film-production-skills` | B | ADAPT | start/action/end state, spatial baseline, continuity preflight | direct text-only authority without state engine | Shot planner |
| Semantic Shot IR | `zhangzhangco/film-production-skills` | B | ADAPT | provider-neutral intermediate representation | provider syntax in canonical schema | compiler boundary |
| Typed Beat/Shot schemas | `XucroYuri/take` | A/B | ADAPT | Zod-style schemas, cross-reference validation, controlled vocabulary | `imagePrompt/videoPrompt` as source of truth | domain validation package |
| Provider transport seam | `XucroYuri/take` | A/B | ADAPT | retryable errors, timeout, rate-limit, provider interface | hard-code current provider list | provider runtime |
| Story/Film Bible/State | `momorzq-oss/Continuity-Studio` | A/B | ADAPT | production memory, film bible, continuity snapshots, restart-safe stages | sequence as only generation authority | State/Production Memory |
| Restart-safe manual/automatic workflow | `momorzq-oss/Continuity-Studio` | A | ADAPT | exact-stage resume, locks, checkpoints | copy entire product UX | production state machine |
| Screenplay/directing causality | `62656456/ai-film-skills` | B | ADAPT | causality, objectives, obstacle, information order, audience effect, earliest-broken-layer repair | all genre presets as core | Story/Director engine |
| Cinematography reasoning | `62656456/ai-film-skills` | B | ADAPT | blocking+camera, visual strategy, complex move start/trigger/phases/end | emotion→camera shortcut | Cinematography engine |
| Character asset method | `62656456/ai-film-skills` | B | ADAPT | script-first design basis, facts vs inference, multi-view reference contract | fixed aesthetic defaults | Reference Bible |
| Screenplay ingest/breakdown | `wassermanproductions/scriptbreak` | B/C | ADAPT | FDX/Fountain/PDF/TXT parsing, elements, bibles, project look | use as story writer | Ingest module |
| Reference-bible discipline | `Nagacash/character-continuity-skill` | B/C | ADAPT | canon frame, turnaround, detail plates, contact-sheet drift audit | make it runtime master | reference methodology |
| Image/video metrics | `TheDesignFounder/DreamLayer-Eval` | B | STUDY/REIMPLEMENT | CLIP/DINO/technical/temporal metrics concepts | copy GPL implementation into incompatible license without review | metric plugin/interface |
| 3D scene map / frustum UX | `LudwigKienle/ai-video-production-editor` | B/C | STUDY | spatial previs concepts, re-film queue UX | GPL core dependency by default | optional previs plugin |
| Storyboard planning | `LinHao-city/StoryMind` | C/B | STUDY | emotional beat + visual anchor concepts | duplicate story/shot authority | no core dependency |
| NLE handoff | `sankar2389/cine-studio` | B/C | ADAPT selectively | NLE/export ideas | duplicate orchestration/provider core | Editorial export |
| Short-form beat map | `Alisa0808/vox-director` | C/B | PLUGIN ONLY | hook/pacing patterns | long-form film grammar | short-form plugin |
| 15-beat diagnostic | `kirklasalle/CineMatrix` | C | STUDY ONLY | optional diagnostic concept | copy code / mandatory fixed formula | optional story framework |

---

# License Risk Notes

- Prefer direct code reuse from permissive MIT/Apache-2.0 sources after file-level verification.
- Treat GPL/AGPL and “All rights reserved” projects as research/architecture references unless a deliberate license strategy is approved.
- License status must be re-verified before any code is imported.
- Architecture ideas are not equivalent to copying source; implementation boundaries should be designed so restricted code is not accidentally pulled into the core.

---

# Core Adoption Principle

```text
One responsibility
→ one canonical authority
→ zero duplicate masters
```

Reference repositories inform implementation. They do not own the project domain model.

# fk:research — Fact-Check & Research Before Scripting

Research and verify real-world events before creating documentary content. This skill MUST be run before `/fk:create-project` for any documentary project.

Usage: `/fk:research <topic> [--language vi] [--depth deep|quick]`

Arguments:
- `topic` — the subject to research (e.g., "US Iran conflict 2025", "Strait of Hormuz crisis")
- `--language` — output language for the research report (default: vi)
- `--depth` — `quick` (3-5 searches) or `deep` (10+ searches with cross-referencing, default: deep)

---

## Step 1: Define Research Questions

Break the topic into 5-7 key research questions:

1. **Timeline** — What are the key events and when did they happen?
2. **Key figures** — Who are the leaders, commanders, and decision-makers involved?
3. **Operations** — What are the real names of military operations, treaties, or agreements?
4. **Outcomes** — What happened? Casualties, territorial changes, diplomatic results?
5. **Current status** — What is the situation now? Ongoing, resolved, ceasefire?
6. **Context** — What caused this? Background tensions, alliances, geopolitical factors?
7. **Impact** — Economic, humanitarian, regional consequences?

## Step 2: Web Search — Gather Facts

For each research question, run targeted web searches using `WebSearch`:

```
WebSearch: "US Iran military conflict 2025 timeline"
WebSearch: "Operation [name] details results"
WebSearch: "Strait of Hormuz crisis 2025 2026"
WebSearch: "[leader name] role Iran conflict"
```

**Search rules:**
- Use multiple search queries per question (at least 2-3 angles)
- Search in both English and Vietnamese for broader coverage
- Prefer official news sources: Reuters, AP, BBC, Al Jazeera, VnExpress, Tuoi Tre
- Cross-reference: a fact must appear in at least 2 independent sources
- Note the publication date of each source

**For `--depth deep`:** Follow up with `WebFetch` on the most relevant articles to get full details, exact quotes, and specific data points.

## Step 3: Build Fact Sheet

Compile verified facts into a structured report:

```markdown
# Research: [Topic]
**Date researched:** YYYY-MM-DD
**Knowledge cutoff note:** [if covering ongoing events]

## Verified Timeline
| Date | Event | Sources |
|------|-------|---------|
| YYYY-MM-DD | [Real event] | [source1], [source2] |

## Key Figures
| Name | Role | Verified |
|------|------|----------|
| [Real name] | [Real title/role] | [source] |

## Real Operation Names
- [Operation name] — [brief description] (source)

## Key Statistics (verified)
- [Stat with source attribution]

## Current Status
[What is the situation as of research date]

## Editorial Angles (our analysis)
- [Our perspective / analysis — clearly marked as opinion]
- [Potential narrative angles that stay truthful]

## Unverified / Uncertain
- [Claims found but not cross-referenced — flag for caution]
```

## Step 4: Validate Against Content Policy

Check the fact sheet against channel content policy rules:

- [ ] All events are real and verified (no invented operations/battles)
- [ ] All dates and timeline are accurate
- [ ] All figures use real names and correct titles
- [ ] No fabricated statistics or casualty numbers
- [ ] Editorial analysis is clearly separated from facts
- [ ] Knowledge cutoff is noted if covering ongoing events

## Step 5: Save Research

Save the fact sheet to `.omc/research/`:

```
.omc/research/{topic_slug}_research.md
```

Example: `.omc/research/us_iran_conflict_2025_research.md`

**Print a summary** to the user:
```
Research complete: [Topic]
- [N] events verified on timeline
- [N] key figures identified
- [N] real operation names confirmed
- Saved to: .omc/research/{slug}_research.md

Ready for /fk:create-project — use this research as the story source.
```

## Step 6: Handoff to Project Creation

When the user proceeds to `/fk:create-project`, the research file serves as the **single source of truth** for:
- `story` field — summary built from verified timeline
- `narrator_text` — must reference only verified events
- Scene descriptions — must depict real events, not invented scenarios
- Character names — must match real figures from the fact sheet

---

## Integration with Pipeline

```
/fk:research "topic"          ← MUST run first
    ↓
/fk:create-project            ← story from research
    ↓
/fk:pipeline                  ← normal pipeline continues
```

## Examples

**Good research → good content:**
```
/fk:research "Strait of Hormuz shipping crisis 2025"
→ Finds: Iran seized 2 tankers in June 2025, US deployed carrier group, 
  oil prices spiked 40%, UN resolution passed in August
→ Story uses these real events with our analysis of strategic implications
```

**Bad (what we did before):**
```
→ AI invented "Operation Epic Fury" (never happened)
→ AI fabricated "April 2026 ceasefire" (not verified)
→ Viewers caught the fake events → lost credibility
```

## Quick vs Deep

| Depth | Searches | Cross-ref | WebFetch | Use when |
|-------|----------|-----------|----------|----------|
| `quick` | 3-5 | 1 source OK | No | Simple/well-known topics |
| `deep` | 10+ | 2+ sources required | Yes, top articles | Complex/recent/controversial topics |

Default is `deep` for documentary content — accuracy matters more than speed.

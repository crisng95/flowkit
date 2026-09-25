# DATA_FLOW.md

```text
Raw Source
  │
  ▼
SourceVersion
  │
  ▼
StoryVersion
  │
  ├── FilmBibleVersion
  │
  └── Sequence → Scene → Beat → Shot
                         │
                         ▼
                 DirectingDecision
                         │
                         ▼
               CinematographyDecision
                         │
                         ▼
                     ShotSpec
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
 EntityVersions    StateSnapshot    SpatialBaseline
        └────────────────┬────────────────┘
                         ▼
                       ShotIR
                         │
                         ▼
                  CompiledRequest
                         │
                         ▼
                    GenerationJob
                         │
                         ▼
                      Artifact
                         │
                         ▼
                      QAResult
                         │
             ┌───────────┴───────────┐
             ▼                       ▼
         RepairPlan              Approved
                                     │
                                     ▼
                              New StateSnapshot
```

Every accepted artifact stores lineage back to all versioned inputs.

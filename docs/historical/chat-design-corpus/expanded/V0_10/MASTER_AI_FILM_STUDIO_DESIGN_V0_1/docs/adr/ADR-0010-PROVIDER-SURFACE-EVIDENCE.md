# ADR-0010 — Provider Surface Separation and Evidence-Bound Runtime Facts

**Status:** PROPOSED / RESEARCH-SUPPORTED  
**Date:** 2026-09-20

## Context

Model brands are exposed through different products with different:
- APIs;
- job handles;
- quotas;
- billing units;
- retention;
- cancellation;
- recovery behavior.

Examples:
- Google Flow vs Gemini API Veo vs Vertex AI Veo;
- local Wan vs Alibaba Model Studio Wan.

## Decision

Canonical provider identity is:

```text
provider
+ provider_surface
+ region
+ model_family
+ model_version
+ profile_version
```

Quotas, pricing, task retention and recovery semantics are stored in versioned `ProviderProfile` evidence.

## Cost

Support multiple billing units rather than `price_per_job`.

## Scheduler

Admission consumes the active ProviderProfile; it does not contain permanent brand-specific constants.

## Consequence

The system needs profile refresh/versioning, but avoids unsafe assumptions when provider products change.

## Evidence

Current official Google Flow, Google Veo, BytePlus Seedance, Alibaba Model Studio Wan and official Wan repository documentation reviewed on 2026-09-20.

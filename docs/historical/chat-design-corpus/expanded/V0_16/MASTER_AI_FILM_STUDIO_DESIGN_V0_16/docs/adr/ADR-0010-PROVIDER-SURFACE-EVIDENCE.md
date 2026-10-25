# ADR-0010 — Provider Surface Separation and Evidence-Bound Runtime Facts

**Status:** PROPOSED / RESEARCH-SUPPORTED  
**Date:** 2026-09-20

## Decision

Canonical provider identity is:

```text
provider + provider_surface + region + model_family + model_version + profile_version
```

Quota, pricing, task retention and recovery semantics are versioned ProviderProfile evidence. The scheduler consumes a profile; it does not embed permanent brand-specific constants.

Cost supports multiple billing units instead of a universal `price_per_job`.

## Consequence

Profile refresh/versioning becomes mandatory, but unsafe cross-product assumptions are prevented.

---
title: Fix Flow batch regression checks
date: 2026-09-12
summary: Corrected stale upscale test contract and Python 3.9 DB annotation import failure.
---

# Fix Flow batch regression checks

## What happened

The FlowKit batch test suite reported one stale upscale assertion and three Python 3.9 import errors in the refresh-URL fixture.

## Decision

Updated the upscale regression test to cover the implemented p0UkFb workflow: source media lookup, workflow id propagation, 1080p tier, and derived upsampled media operation. Added postponed annotation evaluation to agent/db/schema.py, matching the existing module convention and preserving the declared Python 3.10+ runtime contract while keeping the existing Python 3.9 environment import-safe.

## Verification

The former failing batch suite passes 51 tests. The affected Flow batch, Omni, and FlowClient suites pass 146 tests. Importing agent.db.crud under the Python 3.9 virtualenv passes. py_compile and git diff --check pass.

> Historical work record — not durable authority. Prefer docs/specs/ADRs for current decisions.

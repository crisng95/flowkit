# IDEA_INBOX.md
# Project Idea Inbox

## IDEA-001
**Date:** 2026-09-20  
**Source:** Current design discussion  
**Idea:** Build the studio as a best-of-breed architecture rather than one repository fork.  
**Problem solved:** No single audited repo is strongest in story, cinematography, continuity, execution, QA and repair simultaneously.  
**Expected benefit:** Use the strongest subsystem pattern for each responsibility.  
**Impact:** Architecture-wide.  
**Dependencies:** Canonical domain contracts.  
**Risks:** duplicate authorities, license contamination, integration complexity.  
**Research required:** yes.  
**Status:** ACCEPTED as design direction.  
**Official design:** candidate, not frozen.

## IDEA-002
**Date:** 2026-09-20  
**Source:** Current design discussion  
**Idea:** Preserve FlowKit's Entity/Reference/Continuity/Generation Integration/Execution strengths.  
**Problem solved:** Avoid rewriting proven orchestration and reference mechanisms unnecessarily.  
**Expected benefit:** lower implementation risk.  
**Status:** ACCEPTED.

## IDEA-003
**Date:** 2026-09-20  
**Idea:** Replace prompt-as-master with 8-Layer ShotSpec + Shot IR.  
**Problem solved:** prompt bypass, provider lock-in, weak validation.  
**Status:** CANDIDATE — high confidence, requires contract design.

## IDEA-004
**Date:** 2026-09-20  
**Idea:** Implement earliest-responsible-layer targeted repair.  
**Problem solved:** expensive full-shot regeneration and accidental regression of accepted layers.  
**Status:** CANDIDATE — requires QA/repair experiment.

## IDEA-005
**Date:** 2026-09-20  
**Idea:** Add optional spatial/3D previs only for shots requiring it.  
**Problem solved:** text-only spatial ambiguity without imposing 3D cost on all projects.  
**Status:** DEFERRED to post-core phase.

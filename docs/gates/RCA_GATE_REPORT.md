# Phase 7 — Failure Analysis / RCA — Gate Report

**Date:** 2026-08-25  
**Branch:** `develop`  
**Pre-phase HEAD:** `5374f3a`  
**Evidence site:** `digit16.digit-erp.com`  
**Verdict:** **RCA-GATE: PASS**

## Delivered scope

- Command-owned Failure Analysis linked to canonical Service Job, Visit, Installed Equipment and Inspection.
- Full Draft → Inspection → Analysis → Root Cause → Corrective Action → Verification → Closed lifecycle.
- Required root-cause, action, verification and cancellation evidence.
- Configurable repeat-failure look-back and escalation threshold in Service Settings.
- Server-owned repeat count, escalation and priority suggestion.
- Explicit manager command plus audit event for any Job-priority change; no silent mutation.
- Shared typed `FailureAnalysisApi` for Console, Portal and Mobile consumers.

## Verification evidence

| Check | Result |
|---|---|
| RCA focused backend | ✅ 7/7 |
| Full FSM backend regression | ✅ 113/113 (54 + 59) |
| Frontend unit tests | ✅ 10/10 |
| End-to-end surfaces | ✅ 22/22 |
| TypeScript / ESLint / Prettier | ✅ PASS / PASS / PASS |
| Console / Portal / Mobile Web builds | ✅ PASS / PASS / PASS |
| Development migrate twice | ✅ PASS / PASS |
| Ruff / compile / JSON / diff checks | ✅ PASS |

## Known non-blocking risks

- Failure codes are controlled data values, not a new master DocType; a formal taxonomy can be added later without
  changing the aggregate.
- RCA is exposed through the shared contract; dedicated presentation remains part of later screen-completion work.
- Existing Mobile chunk-size and CORE v17 deprecation warnings are unchanged.

**RCA-GATE PASS. Phase 8 — Workshop / RMA / Repair / Replacement is unlocked.**

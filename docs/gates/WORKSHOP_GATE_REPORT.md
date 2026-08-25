# Phase 8 — Workshop / RMA / Repair / Replacement — Gate Report

**Date:** 2026-08-25  
**Branch:** `develop`  
**Pre-phase HEAD:** `8bfe964`  
**Evidence site:** `digit16.digit-erp.com`  
**Verdict:** **WORKSHOP-GATE: PASS**

## Delivered scope

- Extended the existing Service Return into the sole pickup/RMA/workshop lifecycle; no Repair Order duplicate.
- Evidence-gated pickup, inspection, estimate, approval, repair, material wait, testing, QA, dispatch,
  reinstallation, closure and cancellation commands.
- Repaired, Not Repairable, Replacement Recommended and Replaced outcomes.
- Native ERPNext Quotation, Sales Invoice and Stock Entry references and workshop receipt.
- Job/equipment-correlated audit events and a data migration for legacy return states.
- Shared typed `WorkshopApi` for Console, Portal and Mobile.

## Verification evidence

| Check | Result |
|---|---|
| Workshop focused backend | ✅ 6/6 |
| Full FSM backend regression | ✅ 119/119 (54 + 65) |
| Frontend unit tests | ✅ 10/10 |
| End-to-end surfaces | ✅ 22/22 |
| TypeScript / ESLint / Prettier | ✅ PASS / PASS / PASS |
| Console / Portal / Mobile Web builds | ✅ PASS / PASS / PASS |
| Development migrate twice | ✅ PASS / PASS |
| Ruff / compile / JSON / diff checks | ✅ PASS |

## Known non-blocking risks

- The shared contract is complete; the dedicated evidence-rich workshop screen is scheduled for the Console UX
  completion phase. Existing compatibility actions remain available meanwhile.
- Mobile's existing ~1.086 MB main-chunk warning remains a final hardening item.

**WORKSHOP-GATE PASS. Phase 9 — Reports & Certificates is unlocked.**

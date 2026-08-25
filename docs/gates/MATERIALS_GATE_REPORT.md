# Phase 6 — Materials / Spares / Refill — Gate Report

**Date:** 2026-08-25  
**Branch:** `develop`  
**Pre-phase HEAD:** `203910b`  
**Evidence site:** `digit16.digit-erp.com`  
**Verdict:** **MATERIALS-GATE: PASS**

## Delivered scope

- ERPNext-only requirement, availability, reservation, shortage, issue, consumption and unused-return workflow.
- Existing Service Team ERPNext Warehouse link is canonical, with Technician/Service Settings fallback.
- Service Job Item now records requirement type and optional Installed Equipment, never on-hand quantities.
- Native Material Request, Pick List, Stock Entry and Stock Entry Detail correlations to Job/Visit/Equipment.
- Actual consumed cost rollup from submitted ERPNext Stock Entry Details.
- Shared typed `MaterialsApi` for Console, Portal and Mobile.
- Existing `request_parts` retained only as a compatibility alias to the canonical shortage command.

## Ownership proof

No Van Inventory, material ledger, quantity-on-hand DocType or duplicate Item master was created. Tests prove
availability is read from ERPNext Bin, reservation is a submitted Pick List, shortage is a Material Request and
every issue/consume/return is a submitted Stock Entry.

## Verification evidence

| Check                                | Result                |
| ------------------------------------ | --------------------- |
| Materials focused backend            | ✅ 6/6                |
| Full FSM backend regression          | ✅ 106/106 (54 + 52)  |
| Frontend unit tests                  | ✅ 10/10              |
| End-to-end surfaces                  | ✅ 22/22              |
| TypeScript / ESLint / Prettier       | ✅ PASS / PASS / PASS |
| Console / Portal / Mobile Web builds | ✅ PASS / PASS / PASS |
| Development migrate twice            | ✅ PASS / PASS        |
| Ruff / compile / JSON / diff checks  | ✅ PASS               |

## Defect found and closed

The first focused run showed that ERPNext requires `stock_uom` and `conversion_factor` on programmatically
created Stock Entry rows. The adapter now supplies the Item stock UOM and factor 1. A second run exposed that
Stock Entry has no `status` field; the command response now reports the submitted state explicitly. Final result:
6/6.

## Known non-blocking risks

- Pick Lists are the operational reservation document for FSM transfers; ERPNext Bin `reserved_qty` remains its
  native global projection and is not rewritten by FSM.
- Serial/batch values are accepted by the shared command, but broader device UX and offline capture belong to the
  Mobile completion phase.
- The existing Mobile Web chunk-size and CORE v17 deprecation warnings are unchanged.

**MATERIALS-GATE PASS. Phase 7 — Failure Analysis / RCA is unlocked.**

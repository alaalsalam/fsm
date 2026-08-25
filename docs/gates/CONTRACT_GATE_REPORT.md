# Phase 2 — Service Contracts / AMC — Gate Report

**Date:** 2026-08-25  
**Branch:** `develop`  
**Pre-phase HEAD:** `f59ef69`  
**Evidence site:** `digit16.digit-erp.com` (isolated restored test site)  
**Verdict:** **CONTRACT-GATE: PASS**

## Delivered scope

- `Service Contract` canonical aggregate with command-owned Draft/Active/Suspended/Expired/Cancelled lifecycle.
- Customer/company/date validation and Site/equipment/Item Group coverage scope.
- Typed coverage rules for labour, parts, travel, consumables, refill, inspection, and workshop.
- Server-only coverage engine returning Warranty, Contract Covered, Partially Covered, Chargeable, FOC,
  or Not Covered with reason, limits, and remaining entitlement.
- Visit/service entitlements with included, used, and remaining quantities.
- Transactional, row-locked, append-only entitlement consumption with a unique idempotency key.
- Daily retry-safe expiry and renewal-candidate projection.
- Renewal Draft creation that clones terms and resets consumption.
- ERPNext Quotation, Sales Order, Sales Invoice and renewal Quotation links only; no FSM invoice/payment/GL.
- Service Job coverage snapshot fields and a guarded classification command.
- Shared `ContractsApi` contract plus Arabic/English, RTL-aware Console Contracts workbench.

## New DocTypes

| DocType | Kind | Domain owner |
|---|---|---|
| Service Contract | Root | FSM Contracts |
| Service Contract Equipment | Child | FSM Contracts |
| Service Contract Coverage Rule | Child | FSM Contracts |
| Service Contract Entitlement | Child | FSM Contracts |
| Service Entitlement Consumption | Append-only root | FSM Contracts |

No ERPNext master, commercial document, stock ledger, invoice, payment, or accounting concept was duplicated.

## Authorization and retry invariants

- Contract create/update/lifecycle/renewal/consumption require FSM Manager or System Manager and Company scope.
- Customers list/read only their own Customer contracts.
- Technicians may read a Contract only through an assigned Job and cannot consume entitlements.
- Coverage evaluation starts from an authorized Job and validates linked equipment.
- All three runtime `ignore_permissions=True` operations are behind explicit guards and are recorded in
  `docs/security/IGNORE_PERMISSIONS_REGISTER.md`.
- Retrying the same consumption key returns the existing row and does not decrement twice.

## Verification evidence

| Check | Result |
|---|---|
| Contract focused backend | ✅ 13/13 |
| Full FSM backend regression | ✅ 70/70 |
| Frontend unit tests | ✅ 10/10 |
| Contract + baseline E2E at 390px and 1440px | ✅ 20/20 |
| TypeScript typecheck | ✅ PASS |
| ESLint | ✅ PASS |
| Prettier check | ✅ PASS |
| Console build | ✅ PASS |
| Portal build | ✅ PASS |
| Mobile Web build | ✅ PASS; existing non-blocking large-chunk warning only |
| Development migrate #1 | ✅ exit 0 |
| Development migrate #2 | ✅ exit 0 |
| Python compile / JSON parse / diff check | ✅ PASS |

## Defects found during gate cycle

1. Warranty precedence fixture initially used the site's Delivery Date warranty basis while setting only an
   Installation Date. The test now explicitly selects Installation Date; the engine behavior was correct.
2. Manager isolation test initially assumed a restored database contained no other same-company contracts.
   The assertion now proves inclusion of the authorized contract and exclusion of the cross-company contract.
3. Contract list calls used Frappe's deprecated `limit_page_length` name; changed to `limit`.

## Known non-blocking risks

- Public DNS for `digit16.digit-erp.com` is still absent; local Host-routed application/API checks and all
  automated tests pass against the isolated site.
- Mobile's existing approximately 1.086 MB main chunk warning remains unchanged.
- Portal contract/renewal pages are intentionally scheduled for Phase 11; the shared API is already available.

**CONTRACT-GATE PASS. Phase 3 — Preventive Maintenance is unlocked.**

# Phase 3 — Preventive Maintenance — Gate Report

**Date:** 2026-08-25  
**Branch:** `develop`  
**Pre-phase HEAD:** `00d1846cff3023b7e62821ecbbcd5fb75a9da06f`  
**Evidence site:** `digit16.digit-erp.com` (isolated restored test site)  
**Verdict:** **PM-GATE: PASS**

## Delivered scope

- Canonical Maintenance Plan aggregate with explicit Installed Equipment and Plan Line children.
- Days/Weeks/Months/Years recurrence, IANA timezone, forecast horizon, catch-up, DST, lead and grace policies.
- Durable Maintenance Occurrence ledger with deterministic unique identity, reschedule lineage and skip reason.
- Command-owned Plan/Occurrence states and revision supersession without deleting history.
- Daily idempotent scheduler for generation, due/overdue projection and eligible release.
- Row-locked, deterministic campaign release into one canonical Service Job with N equipment rows.
- Unique `maintenance_release_key` prevents duplicate Jobs across retries/concurrency.
- Service Job completion projects all linked released occurrences to Completed; Visit remains attendance evidence only.
- Shared typed `MaintenanceApi` and bilingual RTL-aware Console `/maintenance` workbench with Plans, Schedule,
  Due, Overdue, Occurrences and Generated Jobs views.
- ERPNext Maintenance Schedule/Visit overlap reviewed; no ERPNext commercial, stock, accounting or work-order
  concept was copied.

## New DocTypes

| DocType | Kind | Domain owner |
|---|---|---|
| Maintenance Plan | Root | FSM Maintenance |
| Maintenance Plan Equipment | Child | FSM Maintenance |
| Maintenance Plan Line | Child | FSM Maintenance |
| Maintenance Occurrence | Durable root ledger | FSM Maintenance |

`Service Job` remains the only operational work order. `Customer`, `Item`, `Serial No`, contracts, stock,
sales and accounting truth remain with their established owners.

## Authorization and retry invariants

- Plan create/update/lifecycle/generate/release/skip/reschedule require FSM Manager or System Manager and Company scope.
- Customers can read only their own Plans/Occurrences; Technicians can read an Occurrence only through an assigned released Job.
- All three new runtime `ignore_permissions=True` calls have explicit root authorization/system guards and are recorded in the register.
- Generation and release both have database-enforced deterministic keys; release locks the occurrence group before Job creation.
- Occurrence history is non-deletable; reschedule/revision operations retain cancelled source rows.

## Verification evidence

| Check | Result |
|---|---|
| PM focused backend | ✅ 13/13 |
| Full FSM backend regression | ✅ 83/83 |
| Frontend unit tests | ✅ 10/10 |
| PM + baseline E2E at 390px and 1440px | ✅ 22/22 |
| TypeScript typecheck | ✅ PASS |
| ESLint | ✅ PASS |
| Prettier check | ✅ PASS |
| Ruff lint | ✅ PASS |
| Python compile / JSON parse / diff check | ✅ PASS |
| Console build | ✅ PASS |
| Portal build | ✅ PASS |
| Mobile Web build | ✅ PASS; unchanged non-blocking ~1.086 MB chunk warning |
| Development migrate #1 | ✅ exit 0 |
| Development migrate #2 | ✅ exit 0; no pending migrations |

## Defects found and closed during the gate

1. Frappe returns a `Time` field as `datetime.timedelta`; the timezone converter now normalizes it before `datetime.combine`.
2. Raw string/time representations changed the schedule signature during activation and caused a false revision increment;
   signature time is now canonical seconds and schedule signature is calculated after child validation.
3. The new frontend API input interface required an explicit object spread for the generic client contract.
4. Prettier found two new files requiring formatting; both were normalized and the full check is green.

## Known non-blocking risks

- Public DNS for `digit16.digit-erp.com` remains outside this code gate; all site-scoped bench tests and migrations pass.
- Mobile Web's existing large main-chunk warning is unchanged. Native Android packaging remains gated to Phase 17.
- The restored database emitted one existing Frappe v17 deprecation warning for `limit_page_length` in a prior CORE path;
  it does not fail v16 tests and is not introduced by PM.

**PM-GATE PASS. Phase 4 — Inspection Engine is unlocked.**

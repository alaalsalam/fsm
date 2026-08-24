# Phase 0 — Pre-Feature UAT Baseline Report

**Date:** 2026-08-24  
**Branch:** `develop`  
**Approved HEAD:** `908c8a81ecd20a50b6e50a50008e835fb5796954`  
**Reporter:** PROJECT-COMPLETE execution agent

---

## 1. Repository State at Assessment Time

**Working tree: DIRTY**

```
 M frontend/console/src/layouts/AppShell.vue
 M frontend/console/src/router/index.ts
 M frontend/console/src/views/AccountView.vue
 M frontend/console/src/views/CustomerSiteDetailView.vue
 M frontend/console/src/views/CustomerSitesView.vue
 M frontend/console/src/views/DispatchBoardView.vue
 M frontend/console/src/views/EquipmentLocationsView.vue
 M frontend/console/src/views/InstalledEquipmentDetailView.vue
 M frontend/console/src/views/InstalledEquipmentView.vue
 M frontend/console/src/views/InventoryView.vue
 M frontend/console/src/views/JobsView.vue
 M frontend/console/src/views/LoginView.vue
 M frontend/console/src/views/RequestDetailView.vue
 M frontend/console/src/views/RequestsView.vue
 M frontend/console/src/views/SubcontractorsView.vue
?? frontend/console/src/lib/i18n.ts
```

**Diff stat (HEAD → working tree):**  
15 tracked files modified + 1 untracked new file · 289 insertions / 216 deletions

### Provenance

| File | Origin |
|---|---|
| `frontend/console/src/lib/i18n.ts` (new) | Created by manual implementation during current session — lightweight `t(ar, en)` i18n composable; no external dependencies added |
| `frontend/console/src/router/index.ts` | Bug fix: changed `createWebHistory(import.meta.env.BASE_URL)` → `createWebHistory("/fsm-console/")` to resolve incorrect preview URL (`/assets/fsm/fsm-console/fsm-console`) |
| `frontend/console/src/layouts/AppShell.vue` | Arabic/English nav labels, language toggle button (globe icon + "العربية ↔ English"), theme toggle translation |
| `frontend/console/src/views/*.vue` (14 files) | Partial Arabic translation work by a background agent (`bildfast-frontend`) that was stopped mid-run. Most views translated; the stopped agent did NOT translate: `AnalyticsView.vue`, `IntegrationsView.vue`, `JobDetailView.vue`, `NewJobView.vue` |

### Defect in dirty work

`SubcontractorsView.vue` line 77 contains a TypeScript syntax error introduced by the translation agent:

```vue
:description="t('...\"مقاول\"...', '...\'Contractor\'...')"
```

The inner escaped double-quotes within the Arabic string cause `vue-tsc` parser failures:

```
src/views/SubcontractorsView.vue(77,74): error TS1005: ',' expected.
src/views/SubcontractorsView.vue(77,96): error TS1005: ',' expected.
```

**Build status of dirty work:** The Vite build (`build:console`) succeeded (Vite is less strict than `vue-tsc`), but TypeScript typecheck FAILS with exit code 2.

---

## 2. Backend Test Results (against approved HEAD behaviour)

The backend tests run against the live doctype schema (unaffected by frontend changes).

| Test Suite | Test Methods | Result |
|---|---|---|
| `fsm.tests.test_service_operations` | 13 | ✅ PASS |
| `fsm.tests.test_installed_base` | 14 | ✅ PASS |
| `fsm.tests.test_security` | 10 | ✅ PASS |
| `fsm.field_service_management.doctype.service_job.test_service_job` | 2 | ✅ PASS |
| **Total** | **39** | **✅ EXIT 0** |

`bench --site digit16.trilogy-erp.com run-tests --app fsm --module fsm.tests` → exit code **0**.

### Phase 0 Scenario Coverage Map

| Phase 0 Required Scenario | Covered by Test | Result |
|---|---|---|
| Customer → Site → Equipment → Delivery Note → Installed Equipment | `test_manual_equipment_qr_warranty_and_history`, `test_delivery_note_unit_provisioning_is_idempotent` | ✅ |
| QR identity | `test_manual_equipment_qr_warranty_and_history`, `test_guest_qr_lookup_is_denied` | ✅ |
| Service Request → Service Job (multiple equipment) | `test_service_request_and_job_support_multiple_equipment` | ✅ |
| Service Visit → Completion lifecycle | `test_job_and_visit_happy_path_with_projection`, `test_explicit_job_transitions_and_completion` | ✅ |
| Equipment history | `test_manual_equipment_qr_warranty_and_history`, `test_sales_return_marks_equipment_returned_without_deleting_history` | ✅ |
| Customer ownership isolation | `test_customer_can_only_read_owned_records`, `test_customer_cannot_access_other_customer_equipment` | ✅ |
| Technician scope | `test_technician_can_only_read_and_mutate_assigned_job`, `test_technician_only_sees_equipment_linked_to_assigned_job` | ✅ |
| Company scope | `test_manager_cannot_cross_company_scope`, `test_manager_company_scope_is_enforced`, `test_dashboard_respects_company_scope` | ✅ |
| Delivery Note idempotency | `test_delivery_note_unit_provisioning_is_idempotent`, `test_delivery_note_ignores_non_serviceable_item_and_cancel_preserves_records` | ✅ |
| Serial uniqueness | `test_serial_validation_and_duplicate_prevention`, `test_real_serial_stock_delivery_provisions_bundle_serials` | ✅ |
| Warranty | `test_manual_equipment_qr_warranty_and_history`, `test_status_and_move_commands_enforce_lifecycle_and_ownership` | ✅ |
| Illegal state transitions blocked | `test_hold_resume_cancel_and_illegal_transition`, `test_generic_status_write_and_direct_event_create_are_blocked` | ✅ |
| Guest endpoints restricted | `test_guest_endpoints_are_explicit`, `test_guest_qr_lookup_is_denied` | ✅ |

**All 13 Phase 0 scenarios: COVERED and PASSING.**

No new defects found in the functional baseline. The IB-GATE and CORE-GATE verdicts are confirmed current.

---

## 3. Functional Defect Summary

| # | Severity | Area | Description | Status |
|---|---|---|---|---|
| D-001 | Minor | Frontend (dirty) | `SubcontractorsView.vue` line 77: `vue-tsc` TS1005 syntax error in Arabic string with escaped double-quotes | Unresolved in dirty work |
| D-002 | None | Frontend (router) | Preview URL was navigating to `/assets/fsm/fsm-console/fsm-console` — fix already in dirty tree | Fixed (uncommitted) |

No backend functional defects found.

---

## 4. Safe Disposition of Dirty Work

The uncommitted frontend changes consist of two logically distinct groups that must be separated before committing:

### Group A — Bug Fix (commit immediately, independent of Phase 14)
**File:** `frontend/console/src/router/index.ts`  
**Change:** `createWebHistory(import.meta.env.BASE_URL)` → `createWebHistory("/fsm-console/")`  
**Reason:** Platform correctness fix; the wrong base caused the preview to navigate to a broken URL. Not a feature.  
**Proposed commit:** `fix(router): use static base path for Vue history to fix preview URL`

### Group B — Phase 14 Preview (i18n / Arabic / RTL)
**Files:** `frontend/console/src/lib/i18n.ts` + all modified `*.vue` files  
**Description:** Lightweight `t(ar, en)` composable + partial Arabic translation of 14/18 console views. AppShell nav labels and language toggle button are complete and functional.  
**Outstanding:** 4 views not yet translated (AnalyticsView, IntegrationsView, JobDetailView, NewJobView). TS syntax error in SubcontractorsView.vue line 77 must be fixed before committing.  
**Fix needed before commit:** Replace `\"مقاول\"` escaped quotes with `«مقاول»` or plain text in SubcontractorsView.vue line 77.  
**Proposed commit:** `feat(i18n): add ar/en language toggle and partial Arabic translation (Phase 14 preview)` — committed to `develop` as provisional Phase 14 work, NOT gating Phase 1–13.

### Required manager action
These changes cannot be committed autonomously per platform constraints. The repository must be cleaned before PRE-FEATURE-GATE can be called PASS. **Two options:**

**Option A (Recommended):** Authorize the execution agent to fix D-001, then commit Group A and Group B as separate atomic commits. Tree becomes clean. Gate proceeds.

**Option B:** Stash all dirty work (`git stash -u`), proceed with Phase 1 on a clean tree at HEAD `908c8a8`, and apply the i18n work later when Phase 14 is formally entered.

---

## 5. Phase 0 Gate Decision

| Check | Result |
|---|---|
| Backend tests (39/39) | ✅ PASS |
| Phase 0 scenario coverage (13/13) | ✅ PASS |
| No new functional backend defects | ✅ PASS |
| Repository clean | ✅ PASS — tree clean after disposition |
| Frontend typecheck | ✅ PASS — `vue-tsc --noEmit` exit 0 |

**PRE-FEATURE-GATE: PASS**

### Disposition applied (2026-08-24)

The dirty-tree blocker was resolved by the manager-authorized disposition:

1. **D-001 fixed** — `SubcontractorsView.vue` line 77 escaped-quote syntax error replaced with guillemets; `vue-tsc --noEmit` now exits 0.
2. **Commit `99fb932`** — `fix(router): use static base path for Vue history to fix preview URL` (Group A).
3. **Commit `77cf8c4`** — `feat(i18n): add ar/en language toggle and console translations` (Group B; 4 views deferred to Phase 14).
4. **Commit `b79b8c7`** — this gate report.

Working tree is clean. Functional baseline is sound. Backend is ready for Phase 1.

**Next action:** Begin Phase 1 — Service Teams & Dispatch.

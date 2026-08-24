# GATE-001 final report

- Date: 2026-08-24
- Bench: `/home/erpnext/frappe-bench16`
- Development site: `digit16.trilogy-erp.com`
- Base upstream SHA: `de4dd177781dd0d7eba2aad7825f0c4b19c1fef6`
- Entry revision: `8f73ae2`
- Decision: **GATE-001: PASS**

## Delivered

- Classified all **58/58** whitelisted APIs with actor, action, root, role, company/territory/customer/technician scope, accepted fields, guard, sensitive read/bypass use, risk, and tests.
- Added default-deny backend authorization in `fsm/security`, DocType permission-query/document hooks, Company fields on the four operational roots that require company isolation, and read-only FSM Customer metadata permissions where portal reads are legitimate.
- Guarded every HTTP mutation/transition at its root resource, constrained payload fields and list limits, and scoped all sensitive reads/aggregations.
- Classified all **23/23** `ignore_permissions` occurrences; no generic bypass exists.
- Repaired guest customer registration: translation shadowing, field allowlist, normalized/duplicate identity checks, fixed Website User/FSM Customer role, signup setting, rate limit, savepoint rollback, and Contact→Customer linkage.
- Restored backend test execution using the official owner of `Payment Gateway` (`frappe/payments`) and updated CI installation order.
- Added effective security, Console, Portal, Mobile, and Playwright tests; made token generation format-stable.
- Built the Android debug APK with build-only Java 17 by pinning the Java-17-compatible Capacitor 6 line.
- Accepted ADR-001 through ADR-010 and the target ERD/state/event/screen ownership constraints. No next-phase schema or UI work was started.

## Risks closed

| Risk | Closure evidence |
|---|---|
| Cross-company Manager reads/KPIs | Company User Permission query hooks and negative tests |
| Cross-technician Job mutation | assignment guard and Technician A/B tests |
| Cross-customer portal access | Contact→Customer resolution, Job ownership guard, own message/feedback test, cross-customer negatives |
| Direct child-document bypass | root-aware child hook, Customer/Technician field consistency, negative direct-insert test |
| Unscoped `get_all` counts/totals | permission-aware lists or authorized root/company/warehouse IDs |
| Unreviewed permission bypasses | complete 23-row register with explicit categories |
| Guest role/payload escalation and partial registration | fixed payload/type/role, rate limits, savepoint and rollback tests |
| Missing `Payment Gateway` | official Payments SHA recorded and clean test execution |
| Empty frontend suites | 10 unit/component tests and 6 E2E cases |
| Java 11-only Android host | isolated JDK 17 and SDK 36; default server Java remains 11 |
| Non-deterministic token formatting | generator invokes the repository Prettier contract |
| Scheduler-owned commits | application `frappe.db.commit()` calls removed |

## Validation record

| Command/gate | Result |
|---|---|
| `bench --site digit16-gate.localhost run-tests --app fsm` | PASS, 13/13; clean disposable site |
| `uvx ruff format --check …` / `uvx ruff check …` | PASS for all modified Python files |
| `git diff --check` | PASS |
| `yarn test` | PASS: Console 4, Portal 4, Mobile 2 |
| `yarn typecheck` | PASS across six workspaces |
| `yarn lint` | PASS |
| `yarn format:check` | PASS |
| `yarn build` | PASS: Console, Portal, Mobile |
| `yarn test:e2e` | PASS, 6/6 at 390×844 and 1440×900 |
| `npx cap sync android` | PASS, 11 plugins synchronized |
| Java-17 `./gradlew assembleDebug` | PASS, 423 tasks |
| `bench --site digit16.trilogy-erp.com migrate` twice | PASS; no pending migration failure |
| Node-24 `bench build --app fsm` | PASS |
| `bench … execute fsm.api.get_dashboard_stats` | PASS; scoped zero-value projection |
| Whitelist/DocType recount | 58 APIs; 18 DocTypes unchanged |

Android artifact: `frontend/mobile/android/app/build/outputs/apk/debug/app-debug.apk`, 8,557,123 bytes, SHA256 `3f038163a9f0ade133b7673fe92e2e8242da2788431f5ba4f49c6cb18cb0b7aa`.

## Modified files

Backend/security:

- `fsm/security/{__init__,field_allowlists,permissions,policy,scopes}.py`
- `fsm/{analytics,api,contractors,costing,customers,feedback,integrations,inventory,logistics,messaging,returns,scheduling,tasks,tracking}.py`
- `fsm/hooks.py`
- Service Appointment, Service Job, Service Return controllers/metadata; Technician and Subcontractor metadata
- `fsm/tests/{__init__,test_security}.py`
- `.github/workflows/ci.yml`

Frontend/build:

- Console router/Vite config and three test files
- Portal router/Vite config and three test files
- Mobile Vite/package config and two test files
- `frontend/{package.json,yarn.lock,playwright.config.ts}` and `frontend/e2e/surfaces.spec.ts`
- `frontend/design/{build-tokens.mjs,src/tokens.ts}`
- `.gitignore`, `frontend/.prettierignore`

Documentation:

- ADR-001…ADR-010, `ADR_REVIEW_DECISION.md`, `TARGET_ERD.md`, `STATE_OWNERSHIP_MATRIX.md`, `DOMAIN_EVENTS.md`, `SCREEN_MERGE_MATRIX.md`
- baseline API/permission/baseline/upstream reports
- all files under `docs/security`, `docs/testing`, and this report

## Atomic commits

| Commit | Purpose |
|---|---|
| `2086728` | Central default-deny authorization, scoped reads/writes, registration repair |
| `14e5bbb` | Backend registration/data-isolation tests and Payments CI dependency |
| `06765d1` | Frontend unit/E2E foundation, deterministic tokens, Java-17 native dependency line |
| `a09ea62` | Owned child message/feedback creation and regression coverage |
| Documentation commit containing this report | ADR acceptance, matrices, test/build evidence, final decision |

## Residual risks (not gate failures)

- ADR-009 offline command queue, encrypted cache, conflict resolution, and final device-token design remain target architecture, not implemented functionality. The current Mobile sample fallback must be removed before field trial.
- ADR-010 shared localization catalogues and RTL visual regression remain mandatory next-phase cross-cutting work.
- Mobile's main Vite chunk remains about 1.11MB and triggers a performance warning.
- Shared transport exists, but generated/versioned domain contracts across all three surfaces remain future contract work.
- The first unqualified `bench build` inherited Node 18 and failed its engine check; the isolated Node 24 command passed. Server Node defaults were not changed.
- The host has an unrelated unsigned Webmin APT repository, so `apt-get update` warned/failed; the already indexed official JDK package installed successfully. This is host administration debt outside FSM.

## Environment and cleanup assertion

The only persistent site change was on the designated **development** site `digit16.trilogy-erp.com`: FSM permission metadata migration and installation of the official Payments dependency. Temporary `digit16-gate.localhost` databases/users were deleted after evidence and site directories moved to trash. `/home/erpnext/frappe-bench-startd-prod` and all production sites were untouched. No SwiftService code entered the repository, no functional DocType was added, and CORE-001/Installed Base/PM/screen redesign did not start.

**GATE-001: PASS. Do not start the next phase automatically.**

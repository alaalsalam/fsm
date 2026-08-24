# Test gate report — GATE-001

- Date: 2026-08-24
- Development site: `digit16.trilogy-erp.com`
- Disposable clean test site: `digit16-gate.localhost`
- Result: **PASS**

## Payment Gateway root-cause and repair

The first framework pre-test record generation failed at ERPNext test setup with `frappe.exceptions.DoesNotExistError: DocType Payment Gateway not found`; FSM cases had not started. Source search showed `Payment Gateway` is owned by the official `frappe/payments` app, not FSM or ERPNext core. ERPNext v16 CI installs the Payments `develop` branch before ERPNext. The designated site did not have Payments installed, so this was an install/test dependency mismatch—not an FSM fixture defect and not permission to create a fake DocType.

Repair:

- installed official `https://github.com/frappe/payments` branch `develop`, SHA `86fefa9faf8ad825fe6f08c4753acfe44817900b`;
- installed it on `digit16.trilogy-erp.com` and the clean test site before ERPNext/FSM test execution;
- updated FSM CI to fetch/install Payments in that order;
- corrected the development bench `sites/apps.txt` spelling from `posnext` to its actual module `pos_next`, which otherwise prevented Bench app discovery. This bench-only correction is outside the FSM repository.

## Backend execution

The operational development site already contained test-like ERPNext records that collided with framework bootstrap (`Standard Buying`). A fresh disposable site in the same v16 bench was therefore used to obtain reproducible evidence without deleting operational development data.

Command: `bench --site digit16-gate.localhost run-tests --app fsm`.

| Suite | Tests | Result |
|---|---:|---|
| Existing Service Territory/Service Job | 3 | PASS |
| Customer registration | 4 | PASS |
| Role/data isolation | 6 | PASS |
| Total | 13 | **PASS** |

Covered negative paths include Customer A/B ownership, Technician A/B assignment/mutation, Manager Company A/B isolation, scoped dashboard counts, explicit Guest endpoints, direct child-document bypass, registration duplicates, fixed role/link creation, and transaction rollback.

## Frontend/native execution

| Gate | Result |
|---|---|
| Vitest | 10 tests passed |
| Playwright | 6 tests passed at 390px/1440px |
| Typecheck/ESLint/Prettier | PASS |
| Console/Portal/Mobile builds | PASS |
| Android Java 17 debug | PASS |

The temporary test site is removed after final backend evidence. No production site or production bench was used.

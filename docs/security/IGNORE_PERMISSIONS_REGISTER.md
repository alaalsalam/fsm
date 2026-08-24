# `ignore_permissions` register

Date: 2026-08-24. Search patterns include `ignore_permissions=True`, spaced assignment, and `save/insert(ignore_permissions=True)`. Result: **all 23 occurrences classified**; 15 runtime/setup occurrences and 8 test-fixture occurrences. There is no generic bypass helper.

| Location | Operation | Reachability and guard | Classification | Decision |
|---|---|---|---|---|
| `fsm/setup.py:45` | create FSM roles during install | install/after-migrate hook only | Scheduler/system-only | Approved; deterministic setup cannot depend on an installer user's role. |
| `fsm/integrations.py:145` | create Frappe Webhook | HTTP; `_require_admin` enforces System Manager first | Internal system operation after explicit authorization | Approved; Webhook is a Frappe administrative record. |
| `fsm/messaging.py:51` | append System message | controller-internal reschedule notification | Scheduler/system-only | Approved; no whitelisted caller accepts author or root Job. |
| `fsm/tracking.py:36` | append Technician Location Log | HTTP; current technician is resolved and supplied Job requires assignment | Internal system operation after explicit authorization | Approved; append-only child whose hook updates last location. |
| `fsm/api.py:142` | create Website User | Guest registration; allowlist, normalized email, duplicates, signup setting, fixed Website User, rate limit, savepoint | Approved documented exception | Approved narrowly for self-registration. |
| `fsm/api.py:153` | create ERPNext Customer | Same registration transaction and guard as above | Approved documented exception | Approved narrowly for self-registration. |
| `fsm/api.py:163` | create/link Contact | Same registration transaction; fixed dynamic link and rollback | Approved documented exception | Approved narrowly for self-registration. |
| `fsm/api.py:310` | create Service Appointment | Guest booking; fixed fields, required values, fixed default company, rate limit | Approved documented exception | Approved narrowly for public intake. |
| `fsm/tasks.py:64` | create Notification Log | daily scheduler; recipients are enabled FSM Managers | Scheduler/system-only | Approved; scheduler transaction is framework-owned. |
| `fsm/logistics.py:61` | create Material Request | HTTP; root Job write/assignment guard and item allowlist precede it | Internal system operation after explicit authorization | Approved; ERPNext child operation correlated to authorized Job. |
| `service_job.py:316` | create Sales Invoice | controller system path only when Job completes and setting enabled | Scheduler/system-only | Approved; manual HTTP invoice path uses normal permissions. Failure is logged. |
| `service_appointment.py:58` | create Service Job | document RPC; manager company/territory scope and one-time conversion guard | Internal system operation after explicit authorization | Approved aggregate conversion. |
| `service_appointment.py:83` | create Customer during conversion | same authorized conversion, only if no linked/existing Customer | Internal system operation after explicit authorization | Approved ERPNext bootstrap inside conversion. |
| `service_appointment.py:122` | create Contact during conversion | same authorized conversion with fixed Customer link | Internal system operation after explicit authorization | Approved ERPNext bootstrap inside conversion. |
| `service_return.py:102` | create Stock Entry receipt | document RPC; manager root Job scope, Approved state, warehouse, fixed dispositions | Internal system operation after explicit authorization | Approved; submitted ERPNext stock operation. |
| `fsm/tests/test_security.py:86` | create test User | test runner as Administrator | Approved documented exception | Test fixture only. |
| `fsm/tests/test_security.py:102` | create test Customer | test runner as Administrator | Approved documented exception | Test fixture only. |
| `fsm/tests/test_security.py:109` | create Company User Permission | test runner as Administrator | Approved documented exception | Test fixture only. |
| `fsm/tests/test_security.py:115` | create linked Contact | test runner as Administrator | Approved documented exception | Test fixture only. |
| `fsm/tests/test_security.py:130` | create Technician | test runner as Administrator | Approved documented exception | Test fixture only. |
| `fsm/tests/test_security.py:144` | create Service Job | test runner as Administrator | Approved documented exception | Test fixture only; creates isolation roots. |
| `fsm/tests/test_security.py:159` | create Service Appointment | test runner as Administrator | Approved documented exception | Test fixture only. |
| `fsm/tests/test_security.py:239` | create duplicate-registration User | test runner as Administrator | Approved documented exception | Test fixture only. |

## Enforcement rule

Every future HTTP-reachable bypass must name its root authorization function in this register. A bypass that merely checks authentication, trusts a submitted `customer/company/technician`, or follows a frontend-hidden button is rejected.

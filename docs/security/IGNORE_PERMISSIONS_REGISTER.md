# `ignore_permissions` register

Date: 2026-08-24. Search patterns include `ignore_permissions=True`, spaced assignment, and `save/insert/delete(ignore_permissions=True)`. Result: **all 32 occurrences classified**; 15 runtime/setup occurrences and 17 test/assertion occurrences. There is no generic bypass helper.

| Location | Operation | Reachability and guard | Classification | Decision |
|---|---|---|---|---|
| `fsm/setup.py:45` | create FSM roles during install | install/after-migrate hook only | Scheduler/system-only | Approved; deterministic setup cannot depend on an installer user's role. |
| `fsm/integrations.py:145` | create Frappe Webhook | HTTP; `_require_admin` enforces System Manager first | Internal system operation after explicit authorization | Approved; Webhook is a Frappe administrative record. |
| `fsm/messaging.py:51` | append System message | controller-internal reschedule notification | Scheduler/system-only | Approved; no whitelisted caller accepts author or root Job. |
| `fsm/tracking.py:36` | append Technician Location Log | HTTP; current technician is resolved and supplied Job requires assignment | Internal system operation after explicit authorization | Approved; append-only child whose hook updates last location. |
| `fsm/api.py:142` | create Website User | Guest registration; allowlist, normalized email, duplicates, signup setting, fixed Website User, rate limit, savepoint | Approved documented exception | Approved narrowly for self-registration. |
| `fsm/api.py:153` | create ERPNext Customer | Same registration transaction and guard as above | Approved documented exception | Approved narrowly for self-registration. |
| `fsm/api.py:163` | create/link Contact | Same registration transaction; fixed dynamic link and rollback | Approved documented exception | Approved narrowly for self-registration. |
| `fsm/api.py:332` | create Service Request | Guest intake; fixed fields, required values, fixed default company, rate limit, optional linked current Customer | Approved documented exception | Approved narrowly for public intake. |
| `fsm/tasks.py:64` | create Notification Log | daily scheduler; recipients are enabled FSM Managers | Scheduler/system-only | Approved; scheduler transaction is framework-owned. |
| `fsm/logistics.py:61` | create Material Request | HTTP; root Job write/assignment guard and item allowlist precede it | Internal system operation after explicit authorization | Approved; ERPNext child operation correlated to authorized Job. |
| `service_job.py:316` | create Sales Invoice | controller system path only when Job completes and setting enabled | Scheduler/system-only | Approved; manual HTTP invoice path uses normal permissions. Failure is logged. |
| `service_operations/commands.py:94` | create Service Job | HTTP/document RPC; Request manager company/territory scope, valid Request state, bounded unique idempotency key | Internal operation after explicit authorization | Approved canonical conversion; unique operation key closes retry race. |
| `service_operations/commands.py:223` | create Service Visit | HTTP; manager parent Job scope, active Job, valid schedule, active same-company Technician | Internal operation after explicit authorization | Approved child aggregate creation. |
| `service_operations/events.py:48` | append Service Event Log | callable only from command/projection code; controller requires internal flag | Internal system operation after explicit authorization | Approved append-only audit write. |
| `service_return.py:102` | create Stock Entry receipt | document RPC; manager root Job scope, Approved state, warehouse, fixed dispositions | Internal system operation after explicit authorization | Approved; submitted ERPNext stock operation. |
| `fsm/tests/test_security.py:86` | create test User | test runner as Administrator | Approved documented exception | Test fixture only. |
| `fsm/tests/test_security.py:102` | create test Customer | test runner as Administrator | Approved documented exception | Test fixture only. |
| `fsm/tests/test_security.py:109` | create Company User Permission | test runner as Administrator | Approved documented exception | Test fixture only. |
| `fsm/tests/test_security.py:115` | create linked Contact | test runner as Administrator | Approved documented exception | Test fixture only. |
| `fsm/tests/test_security.py:130` | create Technician | test runner as Administrator | Approved documented exception | Test fixture only. |
| `fsm/tests/test_security.py:144` | create Service Job | test runner as Administrator | Approved documented exception | Test fixture only; creates isolation roots. |
| `fsm/tests/test_security.py:159` | create Service Request | test runner as Administrator with internal command fixture flag | Approved documented exception | Test fixture only. |
| `fsm/tests/test_security.py:239` | create duplicate-registration User | test runner as Administrator | Approved documented exception | Test fixture only. |

## Enforcement rule

Every future HTTP-reachable bypass must name its root authorization function in this register. A bypass that merely checks authentication, trusts a submitted `customer/company/technician`, or follows a frontend-hidden button is rejected.

The nine additional test occurrences are confined to `fsm/tests/test_service_operations.py`: fixture roots plus explicit negative attempts to forge initial state or modify/delete Event Log. They are not imported by runtime code.

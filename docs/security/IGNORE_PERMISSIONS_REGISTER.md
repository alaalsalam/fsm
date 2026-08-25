# `ignore_permissions` register

Date: 2026-08-25. Search patterns include `ignore_permissions=True`, spaced assignment, and `save/insert/delete(ignore_permissions=True)`. Current result: **all 58 occurrences classified**. The CORE register below remains valid; IB adds four runtime command/system occurrences and ten test-fixture occurrences, Teams adds five test-only occurrences, Contracts adds three guarded runtime occurrences plus one test fixture, and Preventive Maintenance adds three guarded runtime occurrences. There is no generic bypass helper.

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
| `installed_base/commands.py` site insert | create Customer Site | HTTP; fixed field allowlist and Manager company/territory scope first | Internal operation after explicit authorization | Approved canonical command. |
| `installed_base/commands.py` location insert | create Equipment Location | HTTP; fixed field allowlist and exact Site write scope first | Internal operation after explicit authorization | Approved canonical command. |
| `installed_base/commands.py` equipment insert | manual Installed Equipment | HTTP; fixed field allowlist and Manager company scope first; controller validates ERPNext links | Internal operation after explicit authorization | Approved canonical command. |
| `installed_base/provisioning.py` equipment insert | provision from Delivery Note | ERPNext submit hook or retry after Manager company scope; eligible Item policy and exact row identity | Internal system operation after explicit authorization | Approved idempotent projection with unique key. |
| `contracts/commands.py` contract insert | create Service Contract | HTTP; fixed field allowlist and Manager company scope precede insert | Internal operation after explicit authorization | Approved canonical Contract command. |
| `contracts/commands.py` renewal insert | create renewal Draft | HTTP; source Contract write/Manager scope precedes fixed clone | Internal operation after explicit authorization | Approved canonical renewal command. |
| `contracts/commands.py` consumption insert | append entitlement consumption | HTTP; Contract Manager scope, Job Manager scope, same Customer/Company, row lock, remaining quantity, and unique idempotency key precede insert | Internal operation after explicit authorization | Approved append-only retry-safe consumption. |
| `maintenance/commands.py` Plan insert | create Maintenance Plan | HTTP; fixed allowlist and Manager Company scope precede insert; controller validates Site/equipment/Contract ownership | Internal operation after explicit authorization | Approved canonical Plan command. |
| `maintenance/engine.py` Occurrence insert | generate/reschedule durable occurrence | Scheduler or HTTP after exact Plan/Occurrence Manager scope; active/open state, deterministic identity and unique constraint | Internal system operation after explicit authorization | Approved durable retry-safe schedule ledger append. |
| `maintenance/engine.py` Service Job insert | release grouped occurrences | Scheduler or HTTP after exact Plan/Occurrence scope; eligible-state filter, row lock, deterministic unique release key; Job controller validates equipment | Internal system operation after explicit authorization | Approved canonical grouped Job release. |
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

The ten IB test occurrences are confined to `fsm/tests/test_installed_base.py` and build ERPNext Customer/Item/Serial/Delivery fixtures or direct negative assertions. They are never imported by runtime code.

The five Teams occurrences in `fsm/tests/test_service_teams.py` and the one Contracts occurrence in
`fsm/tests/test_service_contracts.py` are test fixtures/cleanup only. They are not imported by runtime code.

Preventive Maintenance tests use guarded commands and introduce no test-only bypass.

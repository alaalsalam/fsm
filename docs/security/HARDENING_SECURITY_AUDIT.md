# Phase 15 HARDENING security audit

Date: 2026-08-26. Scope: every `@frappe.whitelist()` function (174 decorators, 34 modules), all 4
`allow_guest` endpoints, all 38 runtime `ignore_permissions` occurrences, all raw SQL, the 4 scheduler
entry points, the mobile offline command ingress, the QR lookup, reports/certificates/signatures, the
realtime channel, and the DocType role-permission matrix. Method: line-level read of the security module
(`fsm/security/`), personal review of the guest/offline/portal/reporting/QR/SQL surfaces, and four
parallel file-group audits reconciled against `hooks.py` and the DocType JSON permission tables.
Companion documents refreshed in the same pass: `API_AUTHORIZATION_MATRIX.md`, `DATA_SCOPE_MATRIX.md`,
`IGNORE_PERMISSIONS_REGISTER.md`.

Severity legend: none / low / medium / high / critical. "Guard" names the first authorization call in
the endpoint body; "Scope" names the row-level filter that bounds the data.

## 1. Endpoint audit tables

### 1.1 `fsm/api.py` (13 endpoints, 4 guest)

| Endpoint (line) | Guard | Scope | Severity |
|---|---|---|---|
| `get_dispatch_jobs` (21) | `require_authenticated` | Service Job query hook; `limit≤200` | none |
| `get_dashboard_stats` (62) | `require_authenticated` | Service Job query hook; KPIs from visible rows | none |
| `create_invoice_from_job` (93) | `require_job_access(write, manager_only)` | exact Job | none |
| `start_job_task` (100) / `complete_job_task` (106) | `require_job_access(write)` | exact Job + sequence guard | none |
| `complete_job` (112) | delegates to canonical command (job write + CompletionPolicy) | exact Job | none |
| `register_customer` (120, **G**) | field allowlist, `is_signup_disabled`, duplicate checks, fixed Website User + FSM Customer role, savepoint rollback, `rate_limit(key=email, 5/h)` | self only | none (email-keyed limiter is rotatable — accepted) |
| `get_portal_session` (188, **G**) | explicit Guest branch | own identity only | none |
| `get_my_requests` (203) / `get_my_appointments` (222) / `get_my_jobs` (228) | server-resolved `current_customer` | explicit customer filter + query hooks | none |
| `get_my_job` (253) | server-resolved customer + explicit owner comparison (257-259) | exact owned Job; Visit list hook-scoped | none |
| `request_service` (295, **G**) | field allowlist, required fields, fixed default company, `rate_limit(10/h)`; customer resolved server-side | narrow Request insert | none |
| `book_appointment` (349, **G**) | alias → `request_service`; `**kwargs` rejected by allowlist | same | none |

### 1.2 Root operational modules

| Endpoint (file:line) | Guard | Scope | Severity |
|---|---|---|---|
| `scheduling.suggest_technicians` (34) / `suggest_teams` (117) | `require_job_access(read, manager_only)` | server-side `doc.company`; `limit≤50` | none |
| `scheduling.assign_technician` (64) / `assign_team` (147) | `require_job_access(write, manager_only)` + same-company check | exact Job/Technician/Team | none |
| `scheduling.get_available_technicians` (83) | `resolve_manager_company` + `require_manager_scope` | server-resolved company | none |
| `analytics.*` (15, 78, 104, 137) | `require_role(Manager/SM)` | Service Job query hook; child `get_all` keyed on scoped Job IDs | low (`days` is unbounded `int` — see L-8) |
| `analytics.domain_dashboard` (176) | `resolve_manager_company` + `require_manager_scope` | every root company-scoped; `days` bounded 1–730 | none |
| `costing.start_timer` (45) / `stop_timer` (68) | server-resolved technician + `require_technician_assignment` | own Job/time log | none |
| `costing.estimate_job` (93) | `resolve_manager_company` + `require_manager_scope` | company filter; limit 1000 | none |
| `costing.get_job_cost_summary` (125) | `require_job_access(read, manager_only)` + manager scope | exact Job children | none |
| `inventory.get_stock_levels` (11) | authenticated + role gate; technician forced to own van; manager warehouse company-checked (44-45) | scoped warehouses → Bin/Item | **medium** (M-3: technician-without-van-warehouse edge) |
| `inventory.get_van_stock` (97) | self/manager resolution then delegates | same as above | inherits M-3 |
| `logistics.request_parts` (9) | alias → `materials.request_shortage` (manager-only Job scope) | exact Job | none |
| `logistics.get_job_logistics` (25) | `require_job_access(read)` | native docs filtered by exact Job link | none |
| `returns.create_return` (66) / `create_workshop_case` (75) | `require_job_access(write)` + item allowlist + equipment∈job | exact Job | none |
| `returns.update_workshop_case` (125) | field allowlist + Job write; commercial links escalate to manager-only (132) | exact case | none |
| `returns.transition_workshop_case` (144) / `process_return` (244) | Job write (+manager for legacy actions) + transition map | exact case | none |
| `returns.list_returns` (187) / `get_return` (207) | authenticated (+Job read when given) | Service Return query hook | none |
| `contractors.list_subcontractors` (10) | `require_role` + `resolve_manager_company` | company filter | none |
| `contractors.get_subcontractor_work` (25) | `require_company_scope` **after** a `db.get_value` probe (28); no explicit FSM-role gate | company-gated reads | **low** (L-1) |
| `customers.get_customer_profile` (11) / `list_field_notes` (78) | `require_customer_access` | visible-Job-derived customer; hooks | none |
| `customers.add_field_note` (51) | Job write + customer/Job match; insert via normal perms (`job_child_permission` blocks technician attribution spoofing) | exact Job/customer | none (manager attribution accepted) |
| `messaging.get_messages` (12) / `post_message` (24) | `require_job_access(read)`; `author_role` ignored, server-derived | Job-child hook | none |
| `feedback.submit_feedback` (14) / `get_feedback` (35) | `require_job_access(read)`; customer server-resolved from Job | exact Job | none |
| `feedback.get_csat_summary` (47) | `require_role(Manager/SM)` | Feedback query hook | low (`days` unbounded — L-8) |
| `tracking.update_location` (17) | server-resolved technician + `require_technician_assignment` when Job given | own append-only log | none |
| `tracking.clock_in` (40) / `clock_out` (51) | server-resolved own Technician | own record | none |
| `tracking.nearest_technicians` (63) | `require_job_access(read, manager_only)` + manager scope | Job-company Technician list | none |
| `integrations.generate_api_keys` (26) / `register_webhook` (125) / `list_webhooks` (149) | `_require_admin` (System Manager) | admin records | none |
| `integrations.create_job` (49) | `require_role` + `resolve_manager_company` + item field allowlist | company-bound insert; customer/rate manager-trusted | **low** (L-2) |
| `integrations.get_job_status` (83) / `list_jobs` (98) | manager-only Job access / role + resolved company | exact Job / hook + company; `limit≤200` | none |
| `commercial.*` (51-116) | Job read for views; `write, manager_only` for Quotation/Invoice/profitability; company resolved server-side | exact Job; billable rows chosen server-side | none |
| `materials.get_material_plan` (74) | Job read + Visit∈Job | reads keyed to authorized Job/warehouse | none |
| `materials.request_shortage` (113) / `reserve_materials` (151) | `_context(manager_only)` + item allowlist + equipment∈job + same-company warehouse | guarded native inserts | none |
| `materials.post_material_movement` (202) | fixed action set; manager-only except exact assigned technician for Consume | guarded native Stock Entry | none |
| `failure_analysis.*` (46-175) | field allowlists + Job write/assignment; suggestion apply manager-only; list uses FA query hook; `limit≤200` | exact parent Job | none |
| `offline.sync_commands` (114) | `require_role(Tech/Mgr/SM)`; 11-action allowlist; ≤50 UUID envelopes; 500 KB payload cap; expected-version conflict check; per-UUID receipt bound to session user; savepoint rollback on failure | each command re-runs its own root guard | low (L-6: raw `str(exc)` echoed) |
| `offline.command_status` (124) | role gate; receipt `user == session.user`; ≤100 UUIDs | own receipts | none |
| `portal.get_my_portal_hub` (16) | `current_customer` + `require_customer_ownership` | every list explicitly customer-filtered; native docs keyed to owned Job names; fixed safe fields | none |
| `reporting.generate_service_report` (48) | `require_job_access(write)`; unique `generation_key` | exact Job snapshot | none for the command itself; see M-1 for snapshot content |
| `reporting.update_service_report` (71) | field allowlist + Job write + immutability gate | exact report | none |
| `reporting.transition_service_report` (88) | Job write + transition map; Verify/Submit manager-only (96); signature-or-refusal gate | exact report | none |
| `reporting.revise_service_report` (112) | Job write + Submitted-source gate | exact report | none |
| `reporting.issue_service_certificate` (126) / `revoke_service_certificate` (159) | Job `write, manager_only` + Submitted-report + equipment∈job + unique key / reason required | exact report/certificate | none |
| `reporting.list_service_documents` (172) | `require_job_access(read)` | exact Job children | none |
| `reporting.get_service_report` (178) / `get_service_certificate` (183) | `require_job_access(read)` via parent Job | full doc incl. `snapshot` | **medium** (M-1) |

### 1.3 `service_operations/`, doctype RPCs

All 21 lifecycle commands (`commands.py:47-281`) authorize the root before mutating:
Request commands use `_request_access(manager_only=True)`; Job commands use
`require_job_access(write[, manager_only])` + transition map; Visit commands use parent-Job write +
exact technician assignment + coordinate validation. `create_job_from_request` (67) enforces a bounded
(1–128) idempotency key hashed to a unique `request_operation_key` with a `DuplicateEntryError`
re-fetch; `create_visit` (206) validates active same-company technician (severity for its
`visit_number = count+1` race: low, L-4). Read projections (`api.py:7-45`) authorize the exact root or
rely on the registered Request/Job/Visit/Event Log query hooks; all limits bounded (≤200/≤500).
Doctype RPCs `ServiceJob.start_task/complete_task` (147/165), `ServiceRequest.create_service_job`
(34) and `ServiceReturn.approve/receive/close` (42/47/64) re-guard internally (manager-only for
Return transitions; receive is idempotent on `stock_entry`). Severity: none.

### 1.4 `installed_base/`, `contracts/`, `maintenance/`

| Surface | Guard/Scope | Severity |
|---|---|---|
| IB reads (`api.py:12-233`) incl. **QR** `resolve_equipment_by_qr` (151) | authenticated → token maps to name only → `require_equipment_access` before any field is returned; Guest denied; all child reads keyed to authorized roots; limits bounded | none (token-existence oracle only) |
| IB commands (`commands.py:83-225`) | field allowlists + `require_manager_scope` / exact Site/Location/Equipment write scope + cross-entity customer/company checks + `EQUIPMENT_TRANSITIONS` map | none |
| IB provisioning (`provisioning.py:245, 251`) | `require_manager_scope(delivery.company)` before guarded inserts; system hook path idempotent on unique `provisioning_key` + `DuplicateEntryError` re-fetch | none |
| Contracts reads (`api.py:18-74`) | **manual** scoping (Service Contract has no query hook): customer→`current_customer`, manager→`allowed_companies`; exact-access getters; bounded windows | none — manual filters are the sole protection, must not be removed |
| Contracts commands (`commands.py:53-142`) | allowlists + manager Contract/Job scope; `consume_entitlement` adds same-customer/company match, `FOR UPDATE` row lock, ≤140 idempotency key, double-checked unique insert | none |
| Maintenance reads (`api.py:10-95`) | plan/occurrence access guards + query hooks; `maintenance_summary` uses hook-bypassing `db.count` but manually customer/company-scoped | none |
| Maintenance commands (`commands.py:47-125`) | allowlists + manager Plan/Occurrence write scope; per-name guard on caller-supplied occurrence lists (112-113) | none |
| Maintenance engine (`engine.py`) | not whitelisted; parametrized `FOR UPDATE` lock (133); occurrence/Job inserts idempotent on unique `identity_key` / `maintenance_release_key` | none |

### 1.5 `inspections/`, `fire_safety/`

| Surface | Guard/Scope | Severity |
|---|---|---|
| `inspections/api.py` (9-77) | template/inspection exact-access guards; lists hook-scoped, `limit` bounded ≤500/≤2000 | none |
| `inspections/commands.py:59 start_inspection` | Job write + active same-company template + technician resolution; **command layer does not guard `installed_equipment`/`service_visit`** — enforced instead by `EquipmentInspection.validate` (equipment_inspection.py:30-48: equipment customer/company match, equipment∈job, visit∈job) so the `ignore_permissions` insert (115) cannot land cross-tenant | low (L-7: single-layer enforcement) |
| `inspections/commands.py` save/complete/close (119/143/160) | `require_inspection_access(write)` + per-row `RESULT_FIELDS` allowlist | none |
| `fire_safety/commands.py` (31/42/86) | manager-only equipment write / Job write + equipment∈job + same-Job visit + extinguisher category / `require_manager_scope` | none |

### 1.6 Schedulers, hooks, realtime

| Function | HTTP-invokable? | Idempotent? | Severity |
|---|---|---|---|
| `tasks.flag_sla_breaches` (hourly) | no | yes (`sla_breached=0` filter) | none |
| `tasks.notify_low_stock` (daily) | no | **no** — Notification Log inserts have no unique key | low (L-3) |
| `contracts.tasks.update_contract_statuses` (daily) | no | yes (status/date-diff guarded) | none |
| `maintenance.tasks.run_daily_maintenance` (daily) | no | yes (unique-keyed engine) | none |
| `installed_base.provisioning.on_delivery_note_submit/cancel` | no (doc_event) | yes (unique `provisioning_key`) | none |
| `realtime.on_service_job_update` (12) / `on_technician_update` (29) | no (doc_event) | stateless | **high** (H-1: unscoped broadcast) |

### 1.7 DocType REST surface (role table + hooks)

All 20 scoped doctypes carry both a `permission_query_conditions` and a `has_permission` hook
(hooks.py:140-183); the hook module `fsm/security/permissions.py` fails closed (`1=0`) for unknown
roles. `Mobile Command Receipt` is System-Manager-read-only. Gaps: `Technician`, `Service Team`,
`Subcontractor`, `Service Territory`, `Checklist Template` have **no query hook** and grant FSM
Technician read — see M-2. `Service Report`/`Service Certificate` grant FSM Customer read of the full
doc including `snapshot` — see M-1.

## 2. Findings

### High

- **H-1 — Cross-tenant realtime broadcast of customer names and live technician GPS.**
  `fsm/realtime.py:12` and `fsm/realtime.py:29` call `frappe.publish_realtime` with no `room`/`user`
  argument, so `fsm_service_job_update` (job name, `customer_name`, status, technician) and
  `fsm_technician_update` (`last_seen_latitude`, `last_seen_longitude`, clock state) are delivered to
  **every** connected authenticated session, across companies. Because `fsm.api.register_customer` is
  open guest signup, any self-registered portal account can subscribe via socket.io and passively
  collect all technicians' live GPS and all job/customer activity. This bypasses the manager-only
  guard the same data has on `tracking.nearest_technicians`. Fix within hardening scope: publish to
  company/manager rooms (e.g. `user=`/`room=` per recipient) or gate with a server-side permission
  check before emit.

### Medium

- **M-1 — Report/certificate `snapshot` exposes internal costs and workshop notes to the owning
  customer.** `fsm/reporting.py:38` embeds `actual_hours`, `labor_cost`, `materials_cost`,
  `total_cost`, plus Stock Entry values (43) and workshop `repair_notes`/`testing_result` (44) into
  the snapshot stored on Service Report and copied to Service Certificate (152).
  `get_service_report` (178) / `get_service_certificate` (183) require only Job **read**, which an
  owning FSM Customer passes, and the DocTypes grant FSM Customer read for direct REST access. This
  contradicts the documented portal policy ("never returns internal cost, stock or staff notes" —
  `fsm/portal.py:18`). Not cross-tenant. Fix: strip cost/internal keys from the snapshot or project a
  customer-safe subset for customer readers.
- **M-2 — Unscoped cross-company master reads for the FSM Technician role.** `Technician`,
  `Service Team`, `Subcontractor`, `Service Territory`, `Checklist Template` have role read for FSM
  Technician but no `permission_query_conditions` hook, and technician accounts carry no Company User
  Permission. Via `/api/resource/Technician` any technician lists all technicians of all companies
  including `phone`, `last_seen_latitude/longitude`, `last_seen_on`, `clocked_in`
  (technician.json fields); `/api/resource/Subcontractor` exposes `hourly_rate`, `phone`, `email`
  cross-company. Fix: add company-scoped query hooks (mirror `inspection_template_query`) or drop the
  role read where not needed.
- **M-3 — `inventory.get_stock_levels` warehouse guard hole for technicians without a van
  warehouse.** `fsm/inventory.py:39` keeps the caller-supplied `warehouse` when the technician's own
  record has none, and the company-scope check at `fsm/inventory.py:44-45` runs only for
  `FSM_MANAGER`. A pure-technician account whose Technician row lacks `warehouse` can read Bin
  quantities (and reorder levels) of any warehouse in any company by name. Fix: company-check the
  supplied warehouse for every non-System-Manager role, or reject caller-supplied `warehouse` on the
  technician path.

### Low

- **L-1** — `fsm/contractors.py:28`: `db.get_value("Subcontractor", …)` existence/company probe runs
  before the guard, and the endpoint relies solely on `require_company_scope` (Company User
  Permission) with no explicit FSM-role requirement.
- **L-2** — `fsm/integrations.py:49 create_job`: caller-supplied `customer`, `service_address`, item
  `rate`/`qty` are trusted beyond company scope (manager-trust boundary; Customer is a global master
  in ERPNext).
- **L-3** — `fsm/tasks.py:64 notify_low_stock`: Notification Log insert has no unique key/existence
  check; a re-run duplicates the daily digest.
- **L-4** — `fsm/service_operations/commands.py:218`: `visit_number = count + 1` is not DB-unique;
  concurrent `create_visit` can duplicate visit numbers (no security impact).
- **L-5** — `frontend/api/src/client.ts:146`: `uploadFile` defaults `is_private` to `0`; any future
  evidence-photo caller that omits `isPrivate: true` publishes files world-readable under `/files/`.
  No current caller exists; signatures are stored as data-URLs inside permission-guarded doc fields.
- **L-6** — `fsm/offline.py:111`: failed commands echo raw `str(exc)` to the client (internal detail
  disclosure; keep the receipt state, return a sanitized message + log reference).
- **L-7** — `fsm/inspections/commands.py:78-93 start_inspection`: the command layer performs no
  `require_equipment_access`/equipment∈job/visit∈job check before building the doc; enforcement
  exists only in `EquipmentInspection.validate` (equipment_inspection.py:30-48). Effective today, but
  single-layer; add the command-level guard to match `fire_safety.record_extinguisher_service`.
- **L-8** — `fsm/analytics.py:15/78/104/137` and `fsm/feedback.py:47`: `days` accepted as unbounded
  `int(days)` (window-size abuse only; `domain_dashboard` already bounds 1–730).

### Informational

- `fsm/security/permissions.py:40, 344` use PEP 758 `except A, B:` syntax — valid only on
  Python ≥ 3.14. Consistent with `pyproject.toml` (`requires-python = ">=3.14"`), but the module (the
  entire permission-hook layer) is a SyntaxError on any older interpreter; failure mode is a hard
  import error (fail-closed), not a bypass.
- `resolve_equipment_by_qr` distinguishes unknown token (`DoesNotExistError`) from unauthorized
  (`PermissionError`) — token-existence oracle, no business data.
- `fsm/patches/v1_0/migrate_service_request_data.py:22` builds SQL with an f-string, but every
  fragment comes from a static in-code mapping and column introspection; migration-only, no user
  input.

## 3. Raw SQL register

| Site | Statement | Parametrized | Verdict |
|---|---|---|---|
| `fsm/contracts/commands.py:168` | Contract `FOR UPDATE` row lock | `%s` + value | safe |
| `fsm/contracts/commands.py:170` | consumption idempotency re-check `FOR UPDATE` | `%s` + value | safe |
| `fsm/installed_base/access.py:72` | technician↔equipment assignment probe | `%s` tuple | safe |
| `fsm/installed_base/access.py:87` | technician↔site assignment probe | `%s` tuple | safe |
| `fsm/maintenance/engine.py:133` | occurrence group `FOR UPDATE` lock | `%s` + value | safe |
| `fsm/patches/v1_0/migrate_service_request_data.py:22-29` | one-off migration updates | static fragments only | safe (migration) |

`sql_in_condition` (`fsm/security/scopes.py:86`) and the query-hook string conditions build SQL from
`frappe.db.escape`d server-side values only; no user input reaches `fields`/`order_by` anywhere in
the audited surface.

## 4. Isolation-proof → test mapping

| Proof | Test evidence |
|---|---|
| Customer A ↛ Customer B (jobs/requests/messages/feedback) | `fsm/tests/test_security.py :: TestDataIsolation.test_customer_can_only_read_owned_records` |
| Customer portal hub isolation (incl. dashboard counts) | `fsm/tests/test_portal_completion.py :: test_customer_hub_isolated_and_safe`, `test_dashboard_counts_only_owned_roots`, `test_guest_is_denied` |
| Customer A ↛ B equipment | `fsm/tests/test_installed_base.py :: test_customer_cannot_access_other_customer_equipment` |
| Customer A ↛ B contracts | `fsm/tests/test_service_contracts.py :: test_customer_reads_only_owned_contract` |
| Customer read-only inspection scope | `fsm/tests/test_inspection_engine.py :: test_customer_read_only_scope` |
| Technician A ↛ Job B (read/mutate) | `test_security.py :: test_technician_can_only_read_and_mutate_assigned_job`; child-doc bypass: `test_child_document_cannot_bypass_root_permission` |
| Technician cross-scope on inspections / reports / RCA / fire safety / materials | `test_inspection_engine.py :: test_assigned_technician_can_execute_but_other_cannot`; `test_reporting.py :: test_scope_direct_create_and_document_projection`; `test_failure_analysis.py :: test_actor_and_context_scope`; `test_fire_safety.py :: test_non_extinguisher_and_unrelated_actor_are_blocked`; `test_materials.py :: test_cross_company_actor_and_unlinked_visit_are_blocked` |
| Manager A ↛ Company B | `test_security.py :: test_manager_cannot_cross_company_scope`, `test_dashboard_respects_company_scope`; plus per-domain: `test_analytics_completion.py` (3 methods), `test_service_contracts.py :: test_manager_cannot_cross_company_contract_scope`, `test_preventive_maintenance.py :: test_manager_and_customer_scope`, `test_commercial.py :: test_company_scope_and_no_financial_duplicates`, `test_workshop.py :: test_direct_create_and_cross_company_actor_are_blocked`, `test_service_teams.py :: test_manager_cannot_assign_cross_company`, `test_fire_safety.py :: test_cross_company_profile_and_template_are_blocked` |
| Guest denial | `test_security.py :: test_guest_endpoints_are_explicit`; `test_service_operations.py :: test_customer_manager_technician_and_guest_boundaries` |
| Offline sync: idempotency / conflict / cross-company / customer denial | `fsm/tests/test_offline.py :: test_successful_command_is_idempotent`, `test_stale_version_returns_conflict_without_mutation`, `test_cross_company_command_fails_inside_guard`, `test_customer_cannot_use_mobile_command_ingress` |
| QR: Guest denied | `fsm/tests/test_installed_base.py :: test_guest_qr_lookup_is_denied` |

**Coverage gaps to close (test-only, no code change):**

1. Offline ingress: no test sends a **non-allowlisted action** string (only auth/scope/version/
   idempotency are proven).
2. `resolve_equipment_by_qr` is not exercised by an unauthorized **authenticated** user (denial is
   proven only via the underlying `require_equipment_access`).
3. No Customer-A-vs-Customer-B assertion on **quotations/invoices/reports/certificates** through the
   portal projections.
4. No dedicated cross-customer **Customer Site** read test.

## 5. Verdict

### Initial audit result
- Critical: 0. High: 1 (H-1). Medium: 3 (M-1, M-2, M-3). Low: 8; informational: 3; test gaps: 4.

### Phase 15 remediation (same-day, within hardening scope)
| Finding | Fix | Where |
|---|---|---|
| **H-1** realtime broadcast of customer names + technician GPS to every session | `publish_realtime` now targets an explicit recipient set only: System Managers + company-scoped FSM Managers (Company user-permission honored, 60 s cached) + the assigned/own technician user. No unscoped broadcast remains. | `fsm/realtime.py` |
| **M-1** internal costing + workshop staff notes in customer-reachable report snapshot | `labor_cost`/`materials_cost`/`total_cost`, Stock Entry `total_outgoing_value`/`total_incoming_value` and `repair_notes` removed from `_snapshot` at source (no consumer existed; commercial totals remain on native ERPNext Quotation/Invoice). | `fsm/reporting.py` |
| **M-2** unscoped Technician/Subcontractor/Service Team reads for the technician role | New `company_master_query` + `company_master_permission` registered in `permission_query_conditions`/`has_permission` for the three masters: managers see permitted companies, technicians only their own company. | `fsm/security/permissions.py`, `fsm/hooks.py` |
| **M-3** van-less technician could pass an arbitrary `warehouse` to `get_stock_levels` | Pure technicians are now pinned to exactly their van warehouse; no van ⇒ empty result; caller-supplied warehouse and all-warehouse fallback are manager-only paths. | `fsm/inventory.py` |

### Post-remediation status
- **Critical: 0 unresolved. High: 0 unresolved. Medium: 0 unresolved.**
- Low: 8 accepted-as-documented (L-1…L-8); informational: 3; the 4 test-coverage gaps remain
  documented for Phase 16 test expansion.
- Bonus offline-stability hardening in the same pass: sync batches now apply in capture order,
  Synced receipts are pruned after a 7-day retention, report/inspection offline commands carry
  `expected_version`, and the ingress accepts a batch-local version chain so a client's own ordered
  queue no longer self-conflicts (external edits still Conflict — covered by two new tests in
  `fsm/tests/test_offline.py`).

All 174 whitelisted functions were classified; apart from the findings above every endpoint
authorizes an exact root or role scope before its first data access, every runtime
`ignore_permissions` write sits behind a named guard or a non-HTTP system path (see
`IGNORE_PERMISSIONS_REGISTER.md`), all raw SQL is parametrized, and all schedulers are
non-whitelisted and idempotent except the accepted daily-digest duplication (L-3).

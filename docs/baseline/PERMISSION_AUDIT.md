# BASE-005 Permission Audit

## Verdict

**Fail — feature development is blocked.** The metadata permission model is simple and understandable, but server-side enforcement is inconsistent. At least 18 application paths use `ignore_permissions=True`; only a subset has a preceding explicit identity/ownership/admin guard. Several sensitive read endpoints use `frappe.get_all`, which bypasses user permission filtering.

## Roles

| Role | Intended scope | Installed desk access | Finding |
|---|---|---:|---|
| FSM Manager | Dispatch, configuration, operational oversight | 1 | Broad CRUD is expected but API role checks are mostly absent |
| FSM Technician | Assigned work execution, location, time, parts | 1 | Metadata grants broad write on Service Job and delete on Time Log; assignment scope is not enforced |
| FSM Customer | Own bookings/jobs/messages/feedback only | 1 | Source requested no desk access; installed value differs; customer scope exists only in selected APIs |
| System Manager | Platform administration | 1 | Appropriate for integration key/webhook administration |

## Permission bypass register

| Path | Bypass purpose | Guard before bypass | Decision |
|---|---|---|---|
| `setup.ensure_roles` | Create roles | Install/migrate lifecycle only | Accept only as migration context; document invariant |
| `api.register_customer` | User/Customer/Contact creation | Guest validation only | Reject until rate limit, duplication, password policy, and atomicity controls exist |
| `api.book_appointment` | Public appointment insert | None beyond field validation | Reject until anti-abuse and guest command guard exists |
| `service_appointment.create_service_job` | Customer/Contact/Job creation | No explicit `has_permission` on appointment | Reject |
| `service_job.make_invoice_from_job` | Sales Invoice insert | No explicit Sales Invoice create permission or FSM command role | Reject; ERPNext-owned command needs guard |
| `logistics.request_parts` | Material Request insert | No explicit MR create permission/job scope | Reject |
| `service_return._make_receipt` | Stock Entry insert/submit | Return transition only; no Stock Entry authorization guard | Reject |
| `costing.start_timer` | Time Log insert | Technician identity, but no assignment/job access check | Reject until assignment guard added |
| `costing.stop_timer` | Time Log save | Technician owns open log lookup | Partial; add document/assignment assertion |
| `tracking.update_location` | Location log insert | Technician identity | Partial; validate job assignment and coordinate bounds |
| `messaging.post_message` | Message insert | Explicit staff/customer job access guard | Acceptable pattern; still validate supplied role is never caller-controlled |
| `messaging.post_system_message` | System message insert | Internal controller call only | Accept as private command; keep non-whitelisted |
| `feedback.submit_feedback` | Feedback insert | Customer/job scope in service layer | Accept only after automated authorization tests |
| `customers.add_field_note` | Note insert | Technician identity | Partial; customer/job relationship and assignment missing |
| `tasks.notify_low_stock` | Notification Log insert | Scheduler context | Accept as scheduler-only internal command |
| `integrations.generate_api_keys` | User save | Explicit System Manager guard | Acceptable pattern |
| `integrations.register_webhook` | Webhook insert | Admin guard | Acceptable pattern if test-proven |
| Controller-generated Contact | Contact insert | No explicit command guard | Reject |

## Read-scope risks

The following endpoint families expose organization-wide data through unrestricted `get_all`/counts without explicit manager authorization: analytics, dashboard statistics, contractor performance, customer profiles/notes, inventory, returns lists, technician availability/proximity, integration job lists, and job logistics. Authentication alone is not authorization.

## Required authorization guard

Every command crossing a permission boundary must perform all applicable checks before mutation:

1. Authenticate the actor and reject Guest unless the command is explicitly public.
2. Assert an allowed command role, not just any authenticated user.
3. Load or identify the target and call `frappe.has_permission(doctype, ptype, doc=doc, throw=True)`.
4. Apply ownership/assignment/tenant scope checks that metadata cannot express.
5. Validate the requested state transition.
6. Only then use a narrowly scoped bypass when ERPNext/Frappe internals require it.
7. Emit an audit event containing actor, command, aggregate, old/new state, and correlation ID.

Public commands additionally require rate limiting, replay/idempotency handling, input bounds, and abuse telemetry.

## Metadata findings

- FSM Technician can write the entire Service Job, not only execution fields.
- FSM Technician can delete Service Time Logs, weakening auditability.
- FSM Customer has create/read on Feedback and Messages, but no DocType-level Service Job read; portal APIs compensate only for selected paths.
- No User Permission strategy constrains technicians to assigned jobs or territories.
- No permission query conditions or `has_permission` hooks are defined.
- No permission tests exist.

## Approval gate

ADR-008 must be accepted and the critical paths above must have automated negative tests before mobile, portal, integrations, or maintenance development proceeds.

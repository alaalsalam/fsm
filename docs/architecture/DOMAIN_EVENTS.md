# ARCH-003 Domain Events

Status: **Proposed contract catalogue**

## Event envelope

Every durable event uses a versioned envelope:

| Field | Meaning |
|---|---|
| `event_id` | Globally unique immutable ID |
| `event_type` | Namespaced past-tense name, for example `service_job.assigned.v1` |
| `occurred_at` | Server UTC timestamp |
| `aggregate_type`, `aggregate_id` | Authoritative aggregate |
| `aggregate_version` | Monotonic optimistic sequence |
| `actor` | User/service/scheduler identity |
| `correlation_id`, `causation_id` | Trace across Request, Job, Visit, and ERPNext documents |
| `payload` | Minimal contract data; no copied full document |
| `schema_version` | Payload version |

Realtime messages are disposable projections, not the durable event record. Publishing occurs after transaction commit; consumers must be idempotent.

## Catalogue

| Event | Producer | Main consumers | Required payload |
|---|---|---|---|
| `service_request.created.v1` | FSM Intake | Console queue, notifications | request, customer/contact, channel |
| `service_request.triaged.v1` | FSM Intake | SLA, dispatch | request, priority, category, SLA target |
| `service_request.converted.v1` | FSM Intake | Job projection, portal | request, job |
| `service_job.planned.v1` | FSM Operations | Dispatch, portal | job, window, address |
| `service_job.assigned.v1` | FSM Operations | Mobile sync, notifications | job, visit, technician IDs |
| `service_job.held.v1` | FSM Operations | SLA, portal | job, reason, next action |
| `service_job.resumed.v1` | FSM Operations | SLA, mobile | job, resolved reason |
| `service_job.completed.v1` | FSM Operations | ERPNext commercial projection, feedback, maintenance | job, completion time, outcome summary |
| `service_job.cancelled.v1` | FSM Operations | Portal, ERP reconciliation | job, reason |
| `service_visit.confirmed.v1` | FSM Work Execution | Portal, dispatch | visit, window |
| `service_visit.travel_started.v1` | FSM Work Execution | Live ETA | visit, technician |
| `service_visit.checked_in.v1` | FSM Work Execution | Job status, audit | visit, time, coordinate evidence/accuracy |
| `service_visit.completed.v1` | FSM Work Execution | Job completion guard | visit, outcome, time, checklist summary |
| `technician.location_recorded.v1` | FSM Workforce | Dispatch/ETA | technician, visit/job, coordinates, accuracy |
| `service_parts.requested.v1` | FSM Operations | ERPNext MR command adapter | job, item/qty requirements |
| `erpnext.material_request.linked.v1` | Integration adapter | Job logistics projection | job, material_request |
| `erpnext.stock_entry.posted.v1` | Integration adapter | Job consumption projection | job, stock_entry, movement type |
| `erpnext.quotation.linked.v1` | Integration adapter | Job commercial projection | job, quotation |
| `erpnext.sales_invoice.submitted.v1` | Integration adapter | Job/portal billing projection | job, invoice, grand total |
| `erpnext.payment_allocated.v1` | Integration adapter | Portal/payment projection | invoice, payment entry, allocated amount |
| `service_feedback.submitted.v1` | FSM Customer Experience | Quality analytics | job, rating, NPS category |
| `maintenance.occurrence_due.v1` | FSM Maintenance | Generator | plan, occurrence, due time |
| `maintenance.occurrence_generated.v1` | FSM Maintenance | Console, audit | occurrence, request/job |
| `maintenance.occurrence_failed.v1` | FSM Maintenance | Operations alert | occurrence, error ID, retry count |

## Command/event separation

API calls are commands in imperative form (`assign_service_job`, `check_in_visit`). Events describe committed facts in past tense. A rejected command emits no business event, though it may emit security telemetry. ERPNext posting commands must return and persist the native document ID before a linked event is published.

## Delivery and privacy

- Use the database transaction/outbox boundary; never publish a durable event before commit.
- Location payload retention and audience are restricted; customer views receive ETA/proximity, not unrestricted technician history.
- Events never include API secrets, full addresses unless necessary, or raw attachment bodies.
- Offline mobile commands carry stable client command IDs; duplicate delivery returns the prior result.

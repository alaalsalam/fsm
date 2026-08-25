# ARCH-002 State ownership matrix

Status: **CORE slice implemented and verified**. Only the named owner authors state; consumers read projections or events.

| Document | Implemented states | State owner | Command actors | Consumers |
|---|---|---|---|---|
| Service Request | Draft, Open, Triaged, Converted, Closed, Cancelled | FSM Intake command service | scoped Manager; public endpoint creates initial Draft/Open under fixed guard | Portal, Console, Job conversion |
| Service Job | Draft, Planned, Scheduled, Dispatched, In Progress, On Hold, Completed, Cancelled | FSM Operations command service | scoped Manager; assigned Technician for execution where allowed | Console, Mobile, Portal, analytics |
| Service Job phase | Planning, Travel, Check-In, Inspection, Diagnosis, On-Site Service, Workshop, Testing, Customer Verification, Closeout | FSM Operations; limited Visit projection | same authorized command actor | operational UI only |
| Service Visit | Planned, Dispatched, En Route, Checked In, In Progress, Checked Out, Completed, Cancelled | FSM Work Execution command service | scoped Manager; exactly assigned Technician | Job projection, Console, Mobile |
| Service Job Task | Pending, In Progress, Done | checklist controller | visible assigned actor | Job completion policy; never status owner |
| Service Event Log | immutable facts | internal event writer | no direct API actor | timelines/audit |
| Technician duty | Off Duty, Available, Busy | FSM Workforce | current Technician and guarded projections | Dispatch |
| Service Return | existing FSM lifecycle | FSM Returns | scoped Manager/assigned actors per controller | Job timeline/ERPNext stock |
| ERPNext commercial/stock documents | native ERPNext states/docstatus | ERPNext | ERPNext-authorized actors | linked Job projections |
| Customer Site | Active, Inactive | FSM Installed Base commands | scoped Manager/System Manager | Console, Portal, equipment validation |
| Installed Equipment | Pending Installation, Active, Inactive, Removed, Returned, Replaced, Disposed | FSM Installed Base commands and guarded ERPNext delivery projection | scoped Manager/System Manager; ERPNext submit/cancel system hook | Console, Portal, assigned Mobile Jobs |
| Equipment warranty | Not Applicable, Active, Expired projection | warranty helper from Item policy + configured date basis | system projection only | all authorized equipment surfaces |
| Delivery provisioning | Completed, Cancelled, Return Reconciled projection | FSM provisioning service after ERPNext lifecycle | ERPNext hook or scoped Manager retry | Delivery Note UI/audit |
| Service Contract | Draft, Active, Suspended, Expired, Cancelled | FSM Contracts command service | scoped Manager/System Manager; scheduler may expire | Console, Portal, coverage engine, renewals |
| Contract coverage | Warranty, Contract Covered, Partially Covered, Chargeable, FOC, Not Covered | FSM coverage engine | deterministic server evaluation; Manager persists Job snapshot | Job, commercial adapter, reports |
| Contract entitlement | included/used/remaining projection | FSM Contracts consumption service | scoped Manager/System process with unique idempotency key | coverage engine, Portal, renewals |

## Projection rules

- Visit En Route/Checked In/In Progress may project Job phase.
- Visit In Progress may move an eligible Scheduled/Dispatched Job to In Progress.
- Visit completion never completes the Job.
- Job completion rejects any non-terminal Visit and applies checklist/evidence policy.
- Request conversion creates Jobs and marks the Request Converted; Visits never write Request.
- Checklist completion never changes Job status.
- Delivery Note submission may create Installed Equipment but never changes ERPNext sales/stock ownership.
- Delivery cancellation/return transitions equipment and retains history; it never deletes the registry.
- Service Visit does not own or duplicate Job equipment rows.
- Coverage classification never creates an invoice; ERPNext commercial documents remain authoritative.
- Entitlement consumption is append-only, row-locked, and retry-safe by unique operation key.

Completed and Cancelled Request/Job/Visit states are terminal in CORE. A future reopen design requires a separately approved command/event contract.

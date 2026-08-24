# ARCH-003 Domain events

Status: **CORE operational audit implemented**.

## Implemented envelope

`Service Event Log` stores `event_id`, `event_type`, reference DocType/name, Request/Job/Visit correlations, actor and actor type, from/to status and phase, server event time, source, correlation ID, and minimal JSON metadata. Records are inserted internally in the command transaction and cannot normally be created, edited, or deleted through document APIs.

## Implemented catalogue

| Domain | Event types |
|---|---|
| Request | `request.opened`, `request.triaged`, `request.converted`, `request.closed`, `request.cancelled` |
| Job | `job.created.from_request`, `job.planned`, `job.scheduled`, `job.dispatched`, `job.started`, `job.started.from_visit`, `job.held`, `job.resumed`, `job.cancelled`, `job.completed`, `job.phase.changed` |
| Visit | `visit.created`, `visit.dispatched`, `visit.travel.started`, `visit.checked_in`, `visit.work.started`, `visit.checked_out`, `visit.completed`, `visit.cancelled` |

Rejected commands write no lifecycle fact. Read access to timelines is authorized against the referenced Request, Job, or Visit root.

## Not claimed by CORE

This table is a durable audit log, not an integration outbox. External delivery, optimistic aggregate versions, causation IDs, event schema versioning, offline replay, maintenance occurrence events, and ERPNext integration events remain future contracts. ERPNext documents themselves remain authoritative for stock, sales, invoices, and payments.

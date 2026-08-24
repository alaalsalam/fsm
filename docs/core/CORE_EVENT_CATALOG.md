# CORE event catalogue

`Service Event Log` is the durable operational audit record. Each row has UUID `event_id`, event type, aggregate reference, ancestor correlations, actor/type, before/after status and phase, server timestamp, source, correlation ID, and minimal JSON metadata. Insert requires the internal event flag; update and delete are rejected by the controller and permissions.

| Aggregate | Events |
|---|---|
| Request | `request.opened`, `request.triaged`, `request.converted`, `request.closed`, `request.cancelled` |
| Job | `job.created.from_request`, `job.planned`, `job.scheduled`, `job.dispatched`, `job.started`, `job.started.from_visit`, `job.held`, `job.resumed`, `job.cancelled`, `job.completed`, `job.phase.changed` |
| Visit | `visit.created`, `visit.dispatched`, `visit.travel.started`, `visit.checked_in`, `visit.work.started`, `visit.checked_out`, `visit.completed`, `visit.cancelled` |

Events are inserted in the same database transaction as their command mutation. A rejected command writes no lifecycle event. The current implementation is an audit log, not an asynchronous outbox; external delivery, aggregate sequence numbers, causation IDs, and offline replay remain explicitly outside CORE.

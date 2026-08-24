# ADR-003: Service Job is the canonical operational aggregate

- Status: Accepted
- Date: 2026-08-24

## Context

Field service products often accumulate Service Request, Work Order, Repair Order, RMA, PM Visit, and Closure documents that independently claim to be “the job.” This creates divergent state and billing/stock links.

## Decision

`Service Job` is the sole canonical work order and operational aggregate root. It owns the service commitment, operational scope, priority, plan, equipment, outcome, and correlation to Visits and ERPNext documents. It is explicitly **not a God Document**: intake remains in Service Request, attendance evidence remains in Service Visit, equipment masters remain in ERPNext, and stock/billing/collection states remain in their native ERPNext documents. Depot repair, installation, corrective, preventive, calibration, and replacement are Job types/outcomes—not competing work orders.

Supporting Request and Visit records have narrow boundaries defined by ADR-005. Closure is a Job transition, not a separate aggregate.

## Consequences

- Every operational command carries a Service Job ID once a request is converted.
- RMA/repair/replacement screens merge into Job workflows.
- ERPNext documents link to Job but retain their own authoritative states.
- Existing Service Return remains a bounded returns process, not a second job.

## Approval gate

No proposed DocType or screen may duplicate Job scope or own a conflicting operational status.

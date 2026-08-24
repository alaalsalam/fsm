# CORE data model

Status: implemented and verified on 2026-08-24.

## Canonical model

```text
ERPNext Customer 1 ── N Service Request 1 ── N Service Job 1 ── N Service Visit
                                      │              │
                                      └──────────────┴── N Service Event Log
```

`Service Job` is the only operational work order. `Service Request` owns intake and triage; it may produce multiple Jobs. `Service Visit` records one field attendance attempt and never owns billing, stock, or Job completion. `Service Event Log` is append-only evidence correlated to Request, Job, and Visit.

## Physical DocTypes

| DocType | Owner | Key relation/invariant |
|---|---|---|
| Service Request | FSM Intake | Starts Draft; status changes by command; `1:N` Jobs |
| Service Job | FSM Operations | Canonical aggregate; optional immutable Request origin; `1:N` Visits |
| Service Visit | FSM Work Execution | Required `service_job`; numbered attendance attempt |
| Service Event Log | FSM Operations audit | Immutable; internal append only; links all available ancestors |

The implementation has 20 FSM DocType JSON definitions: 15 root/single records and five child tables. The approved pre-CORE revision had 18. `Service Appointment` was renamed to `Service Request`; `Service Visit` and `Service Event Log` were added. No duplicate Appointment runtime DocType remains.

## ERPNext boundary

ERPNext remains authoritative for Customer, Contact, Address, Item, warehouse balances, Material Request, Stock Entry, Delivery Note, Quotation, Sales Invoice, Payment Entry, and accounting state. FSM stores links and operational projections only.

## Integrity controls

- Generic inserts cannot forge non-initial Request, Job, Visit, or Event states.
- Generic saves cannot mutate Request/Job/Visit lifecycle fields.
- `(service_request, idempotency_key)` is represented by the unique SHA-256 `request_operation_key`, making Request-to-Job retries deterministic.
- Checklist rows provide completion evidence but cannot transition the Job.
- Completed and Cancelled states are terminal in CORE; no reopen command exists in this phase.

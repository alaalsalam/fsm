# Service Contracts / AMC data model

Status: implemented in Phase 2. Domain owner: **FSM Contracts**.

## Aggregate

`Service Contract` is the aggregate root. It owns its operational period, lifecycle, coverage scope,
coverage rules, SLA terms, and entitlements. It links to ERPNext Quotation, Sales Order, and Sales Invoice;
those ERPNext documents remain the sole commercial and accounting truth.

| Document | Kind | Responsibility |
|---|---|---|
| Service Contract | Root | Customer/company, lifecycle, period, SLA, renewal and ERPNext references |
| Service Contract Equipment | Child | Customer Site plus optional exact equipment or Item Group scope |
| Service Contract Coverage Rule | Child | Typed labour/parts/travel/consumables/refill/inspection/workshop coverage |
| Service Contract Entitlement | Child | Included, used, and remaining visit/service allowance |
| Service Entitlement Consumption | Append-only root | Transactional consumption evidence with a unique idempotency key |

An empty scope table means customer-wide coverage. A site-only row covers the site. An equipment or Item
Group value narrows that row. Customer and company consistency are validated against Customer Site and
Installed Equipment.

## Lifecycle

```text
Draft ──> Active ──> Suspended ──> Active
  └────> Cancelled     ├────────> Expired
Active ────────────────┼────────> Cancelled
Suspended ─────────────┴────────> Cancelled
```

Only application commands change status. Expired and Cancelled are terminal. The daily scheduler expires
past-due Active/Suspended contracts idempotently and marks contracts within 30 days as renewal candidates.

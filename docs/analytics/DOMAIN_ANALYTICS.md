# Domain Analytics

The Phase 12 scorecard is a read-only projection over the canonical FSM and ERPNext records. It does not create an analytics ledger or duplicate operational state.

## Contract

`fsm.analytics.domain_dashboard(days=90)` requires FSM Manager or System Manager scope and resolves the caller's Company before querying any root. The bounded window is 1–730 days.

The response groups KPIs into `executive`, `operations`, `maintenance`, `teams`, `contracts`, and `equipment`. Revenue comes from submitted ERPNext Sales Invoices linked to Service Jobs; costs are Service Job operational rollups. Team, contract, inspection, failure, return, occurrence, equipment and site metrics are restricted to the resolved Company roots.

## Ownership

| Metric family | Source of truth |
|---|---|
| Customers and commercial revenue | ERPNext Customer / Sales Invoice |
| Sites, installed equipment, jobs and visits | FSM canonical operational records |
| Stock and material cost | ERPNext Stock documents projected to Service Job |
| PM compliance | Maintenance Occurrence |
| Inspection quality | Equipment Inspection |
| Team productivity | Service Job / Service Visit / Customer Feedback |
| Contract utilization | Service Contract Entitlement |
| Failure and repair trends | Failure Analysis / Service Return |

All calculations are projections and may be rebuilt from their owning records.

## Safety and scale

- Company is server-derived; the client cannot choose another Company.
- Non-manager actors are denied.
- Root queries are Company scoped before child rows are read.
- Windows and result limits are bounded; the hardening gate owns larger-volume profiling and pagination evidence.

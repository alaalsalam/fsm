# ADR review decision — GATE-001

- Review date: 2026-08-24
- Scope: ADR-001 through ADR-010
- Decision: Accepted with the constraints below
- Authority boundary: architecture approval only; it does not authorize CORE-001, new functional DocTypes, production changes, or screen redesign.

| ADR | Decision | Binding constraints | Rejected alternatives | Consequence |
|---|---|---|---|---|
| ADR-001 | Accepted | KodLyft FSM remains the sole codebase. | Merging or copying SwiftService source/schema/assets. | All implementation and provenance stay in this repository. |
| ADR-002 | Accepted | SwiftService is capability evidence only; every parity row has a target decision. | Porting its implementation or treating its schema as authoritative. | Any accepted capability is independently designed and tested clean-room. |
| ADR-003 | Accepted | Service Job is the canonical work order, not a God Document. | Competing work orders; moving Request, Visit, equipment-master, stock, or accounting truth into Job. | Commands correlate through Job while bounded records retain ownership. |
| ADR-004 | Accepted | ERPNext v16 owns sales, stock, invoicing, collection, tax, and ledgers. | FSM replicas of Item, Warehouse, Invoice, Payment, or ledger state. | FSM stores native links and operational projections only. |
| ADR-005 | Accepted | Request 1:N Jobs; Job 1:N Visits; Job 1:N Job Equipment. No duplicate Request/Appointment concept. | One combined lifecycle document or competing operational status owners. | Intake, commitment, and attendance evolve independently with explicit correlations. |
| ADR-006 | Accepted | Multi-equipment Job is mandatory; ERPNext Item/Serial No/Asset remain masters. | One Job per unit as the only model; FSM Installed Base duplication. | A future Job Equipment child relation is required, but not authorized in this gate. |
| ADR-007 | Accepted | Idempotency key `(plan, revision, due_at_utc)`, IANA timezone/DST policy, immutable revisions. | Direct recurring Job creation without an occurrence ledger; rewriting generated history. | Retries and plan changes remain deterministic and auditable. |
| ADR-008 | Accepted | Backend default-deny; role plus company/customer/technician/territory root scope; every bypass registered. | Frontend-only security, generic bypass helpers, unscoped `get_all`. | The `fsm.security` layer and negative tests are mandatory for future endpoints. |
| ADR-009 | Accepted as target architecture | Encrypted read cache, idempotent command queue, server reconciliation, no offline financial/stock/assignment commands. | Local CRUD mirror or long-lived API key/secret as final device session. | Current online fallback is not claimed as completed offline architecture. |
| ADR-010 | Accepted as mandatory cross-cutting rule | Shared Arabic/English catalogues, RTL-aware design tokens/components, stable API error codes. | Per-screen translation and physical left/right styling. | Every future screen and contract must pass localization and RTL checks. |

## Approval record

The review confirms that the required architectural choices are final for subsequent planning. GATE-001 validates the current permission model and build/test foundation only. Implementation of Service Request, Service Visit, Job Equipment, Installed Base, preventive maintenance, or redesigned screens requires a separate authorized phase and migrations designed from these accepted decisions.

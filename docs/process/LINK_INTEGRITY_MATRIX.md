# Link integrity matrix

| Source → target | Cardinality | Owner | UI/API visibility | Lifecycle rule |
|---|---:|---|---|---|
| Delivery Note → Installed Equipment | 1:N | ERPNext/FSM provisioning | After-Sales, equipment API | submitted non-return only; deterministic key |
| Request → Job | 1:N | Request command | Request detail/Job | idempotent per operation key |
| Contract → Plan | 1:N by site | PM orchestration | Contract/PM | preview-first; reuse existing |
| Plan → Occurrence | 1:N | PM engine | Maintenance | deterministic identity/revision |
| Occurrence → Job | N:1 grouped | PM release | Maintenance/Job | deterministic release key |
| Job → Visit | 1:N | Visit command | Job/Visits/Mobile | active planned Job only |
| Job → Equipment | 1:N child links | Job | Job/Equipment history | same customer/company; no duplicates |
| Job/Equipment → Inspection | 1:N | Inspection | Job/Mobile/history | result owns equipment outcome |
| Job/Equipment → Workshop | 1:N | Service Return | Job/Returns | completion blocks open case |
| Job → Report → Certificate | 1:N | Reporting | Job/Portal | immutable submitted snapshot |
| Job → Quotation/Invoice | 0:1 each | ERPNext | Job commercial | no parallel ledger |

All reads pass DocType permission query conditions or explicit authorization guards.

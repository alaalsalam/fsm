# Materials workflow

FSM does not own a stock ledger. A Service Job Item expresses requirement intent; every stock quantity and
movement comes from ERPNext.

| Step           | ERPNext authority               | FSM behavior                                                                                |
| -------------- | ------------------------------- | ------------------------------------------------------------------------------------------- |
| Requirement    | Service Job Item intent         | Item, quantity, Spare/Consumable/Refill, optional Installed Equipment                       |
| Availability   | Warehouse + Bin                 | Read `actual_qty`; Team warehouse wins over Technician and Settings fallbacks               |
| Reservation    | submitted Pick List             | Correlate to Job/Visit; the Pick List is the auditable operational reservation              |
| Shortage       | Material Request                | Create a draft Material Transfer request for native approval/procurement                    |
| Transfer/issue | Stock Entry / Material Transfer | Move central stock to the Team/Van Warehouse                                                |
| Consume        | Stock Entry / Material Issue    | Issue from Team/Van and correlate Job/Visit/Equipment                                       |
| Return unused  | Stock Entry / Material Transfer | Move unused stock from Team/Van to an explicitly selected receiving Warehouse               |
| Actual cost    | submitted Stock Entry Detail    | Sum consumed `basic_amount`; Job planned item amount is used only before consumption exists |

Supported refill materials are normal ERPNext Items (for example DCP, CO2, seals, pins, hoses, gauges and
valves). No special product master or refill inventory is introduced.

## Authorization

- Plan reads require Job read access.
- Requirement, reservation, transfer, issue and return require manager-scoped Job access.
- Consumption permits the exactly assigned Technician or scoped Manager.
- Visit must belong to the Job; optional Installed Equipment must be a Job equipment row.
- Every Warehouse must be active, non-group and belong to the Job company.
- Privileged ERPNext writes occur only after those guards and are registered in the permission audit.

## Shared contract

`frontend/api/src/materials.ts` exposes one `MaterialsApi` to Console, Portal and Mobile. Surfaces may present
different tasks, but must not reimplement document semantics or quantities.

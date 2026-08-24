# Service Appointment migration report

## Result

`fsm.patches.v1_0.rename_service_appointment` renames the existing DocType to `Service Request` only when the old name exists and the new name does not. The patch is recorded in `tabPatch Log`, repeated migrate runs are no-ops for the rename, and the development database contains Service Request, Service Visit, and Service Event Log with no Service Appointment DocType.

Portal booking calls `request_service`; Console routes are `/requests` and `/requests/:name`; Job links target Service Request. The runtime does not contain a parallel Appointment aggregate.

## Repository reference classification

| Remaining reference | Classification | Decision |
|---|---|---|
| `fsm/patches.txt`, `fsm/patches/v1_0/rename_service_appointment.py` | intentional legacy migration compatibility | retained |
| `fsm.api.get_my_appointments`, `fsm.api.book_appointment` | intentional rolling client compatibility | retained as documented deprecated forwarding aliases; no Appointment DocType access |
| `docs/baseline/**`, `docs/gates/GATE-001_FINAL_REPORT.md`, `docs/core/CORE_WORKTREE_INVENTORY.md` | harmless historical evidence | retained |
| ADR-005 and pre-CORE architecture review wording | harmless decision history, with implemented state now documented here | retained |

All user-visible runtime Appointment wording was removed. Security and architecture matrices were updated to the Request/Job/Visit model. No orphaned code import or active DocType reference remains.

## Schema delta

- Before: 18 FSM DocType JSON definitions.
- After: 20.
- Renamed: Service Appointment → Service Request.
- Added: Service Visit, Service Event Log.
- Removed as runtime duplicate: Service Appointment.

The patch preserves the physical renamed table/data through Frappe's DocType rename mechanism rather than copying records into a second table.

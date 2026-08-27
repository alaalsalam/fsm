# Current system map

Baseline: `2bc61bc2e692a251fdd8d900a7730cb6c8ec3684` on `develop`.

The audited product contains 44 FSM DocTypes. ERPNext owns Customer, Address, Contact, Project, Item, Serial/Batch, Delivery Note, Sales Order, Quotation, Sales Invoice, stock movements, warehouses and payments. `Service Job` is the operational aggregate; Request, Visit, Inspection, Return/Workshop, Report and Maintenance Occurrence own their distinct lifecycles.

| Domain | Root records | Supporting/internal records | Entry and exit |
|---|---|---|---|
| Intake | Service Request | Service Event Log | Portal/Console → Service Job |
| Installed base | Customer Site, Installed Equipment, Equipment Location | — | Delivery Note/manual provisioning → service history |
| Operations | Service Job, Service Visit | Job Equipment, Job Item, Job Task, Time Log, Message | Request/Occurrence → Report/Commercial/Completion |
| Teams | Service Team, Technician, Territory, Subcontractor | Team Member, Skill, Certification, Location Log | Assignment → Visit execution |
| Contracts | Service Contract | Coverage Rule, Contract Equipment, Entitlement, Consumption | Commercial terms → coverage/PM/renewal |
| PM | Maintenance Plan, Maintenance Occurrence | Plan Equipment, Plan Line | Contract/manual plan → grouped Job → next due |
| Inspection/RCA | Equipment Inspection, Failure Analysis | Template, Template Item, Inspection Result | Job equipment → outcome/material/workshop |
| Workshop | Service Return | Return Item | Job/equipment → receipt/repair/return |
| Reporting | Service Report, Service Certificate | — | Execution snapshot → signed/submitted evidence |
| Platform | Service Settings, Mobile Command Receipt | Checklist Template/Item, Feedback, Field Note | policy/offline/audit helpers |

Console routes were audited in `frontend/console/src/router/index.ts`; Portal and Mobile routes remain separate surfaces over the same command APIs. Schedulers cover PM generation/release, contract status and operational projections. ERPNext document hooks provision/cancel equipment from Delivery Note. No DocType was deleted or duplicated in this phase.

# BASE-002 DocType Inventory

Source: KodLyft FSM at upstream SHA `de4dd177781dd0d7eba2aad7825f0c4b19c1fef6`. The inventory contains 12 standalone DocTypes, one Single, and five child tables.

| DocType                 | Kind                       | Domain owner            | Child tables                       | External links                                                                                          | Controller behavior                                                                               |
| ----------------------- | -------------------------- | ----------------------- | ---------------------------------- | ------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| Service Job             | Canonical aggregate        | FSM Operations          | Service Job Task, Service Job Item | Customer, Contact, Address, Service Territory, Technician, Checklist Template, Quotation, Sales Invoice | Defaults, checklist seeding, totals/costs, derived state, SLA, technician state, optional invoice |
| Service Appointment     | Standalone                 | FSM Intake              | —                                  | Customer, Service Territory, Service Job                                                                | Public booking/intake and one-way conversion to Service Job                                       |
| Technician              | Standalone                 | FSM Workforce           | Technician Skill                   | User, Subcontractor, Service Territory, Warehouse                                                       | Data controller only                                                                              |
| Technician Location Log | Standalone event/log       | FSM Workforce           | —                                  | Technician, Service Job                                                                                 | Captures actor/time and updates technician last-known position                                    |
| Service Territory       | Standalone tree-like       | FSM Dispatch            | —                                  | Parent Service Territory                                                                                | Data controller only; not a Frappe tree DocType                                                   |
| Checklist Template      | Standalone template        | FSM Work Execution      | Checklist Template Item            | —                                                                                                       | Data controller only                                                                              |
| Service Time Log        | Standalone log             | FSM Work Execution      | —                                  | Service Job, Technician                                                                                 | Validates interval and recomputes parent job costs                                                |
| Customer Field Note     | Standalone note            | FSM Customer Context    | —                                  | Customer, Service Job, Technician                                                                       | Data controller only                                                                              |
| Service Job Message     | Standalone message         | FSM Collaboration       | —                                  | Service Job, User                                                                                       | Stamps author and publishes realtime update                                                       |
| Service Feedback        | Standalone feedback        | FSM Customer Experience | —                                  | Service Job, Customer                                                                                   | Validates rating/NPS and derives metadata                                                         |
| Service Return          | Standalone process         | FSM Returns             | Service Return Item                | Service Job, Customer, Warehouse, Stock Entry                                                           | Guarded state methods and ERPNext Material Receipt creation                                       |
| Subcontractor           | Standalone party extension | FSM Workforce           | —                                  | Service Territory                                                                                       | Data controller only                                                                              |
| Service Settings        | Single                     | FSM Configuration       | —                                  | Service Territory, Checklist Template, Warehouse                                                        | Data controller only                                                                              |
| Service Job Task        | Child table                | FSM Work Execution      | —                                  | —                                                                                                       | Checklist step state and timestamps                                                               |
| Service Job Item        | Child table                | FSM Cost/Consumption    | —                                  | Item, UOM                                                                                               | Quantity, rate, amount; no stock ledger ownership                                                 |
| Service Return Item     | Child table                | FSM Returns             | —                                  | Item, UOM                                                                                               | Return quantity and disposition                                                                   |
| Technician Skill        | Child table                | FSM Workforce           | —                                  | —                                                                                                       | Skill and proficiency                                                                             |
| Checklist Template Item | Child table                | FSM Work Execution      | —                                  | —                                                                                                       | Template step and description                                                                     |

## State fields

| DocType             | States                                                                 |
| ------------------- | ---------------------------------------------------------------------- |
| Service Appointment | Open, Scheduled, Converted, Cancelled                                  |
| Service Job         | Draft, Scheduled, Assigned, In Progress, On Hold, Completed, Cancelled |
| Service Job Task    | Pending, In Progress, Done                                             |
| Service Return      | Draft, Requested, Approved, Received, Closed, Cancelled                |
| Technician          | Available, On Job, Off Duty                                            |
| Subcontractor       | Active, Inactive                                                       |

## Permission rows

Legend: R read, W write, C create, D delete.

| DocType                 | System Manager | FSM Manager | FSM Technician | FSM Customer |
| ----------------------- | -------------- | ----------- | -------------- | ------------ |
| Checklist Template      | RWCD           | RWCD        | R              | —            |
| Customer Field Note     | RWCD           | RWCD        | RWC            | —            |
| Service Appointment     | RWCD           | RWCD        | RW             | —            |
| Service Feedback        | RWCD           | RWCD        | R              | RC           |
| Service Job             | RWCD           | RWCD        | RW             | —            |
| Service Job Message     | RWCD           | RWCD        | RC             | RC           |
| Service Return          | RWCD           | RWCD        | RWC            | —            |
| Service Settings        | RWCD           | RWCD        | —              | —            |
| Service Territory       | RWCD           | RWCD        | R              | —            |
| Service Time Log        | RWCD           | RWCD        | RWCD           | —            |
| Subcontractor           | RWCD           | RWCD        | R              | —            |
| Technician              | RWCD           | RWCD        | R              | —            |
| Technician Location Log | RWCD           | RWCD        | RC             | —            |

Child tables have no direct permission rows and inherit access through their parent. There are no Workflow fixtures; state enforcement is controller/API code plus editable Select fields.

## Controllers

Controllers with material behavior are `ServiceJob`, `ServiceAppointment`, `ServiceReturn`, `ServiceTimeLog`, `TechnicianLocationLog`, `ServiceJobMessage`, and `ServiceFeedback`. The remaining eleven controller classes are data-only subclasses of `Document`.

## Reports and dashboards

No Frappe Report, Dashboard, Dashboard Chart, Number Card, or Workspace files are present. Console analytics is implemented through whitelisted aggregate endpoints and Vue views, so it must not be represented as native Frappe reporting coverage.

## ERPNext custom fields

| ERPNext DocType       | Field                                                         | Type        | Target                                              |
| --------------------- | ------------------------------------------------------------- | ----------- | --------------------------------------------------- |
| Material Request      | `fsm_service_job`                                             | Link        | Service Job                                         |
| Material Request      | `fsm_service_visit`                                           | Link        | Service Visit                                       |
| Material Request Item | `fsm_installed_equipment`                                     | Link        | Installed Equipment                                 |
| Pick List             | `fsm_service_job`, `fsm_service_visit`                        | Link        | Service Job, Service Visit                          |
| Pick List Item        | `fsm_installed_equipment`                                     | Link        | Installed Equipment                                 |
| Stock Entry           | `fsm_service_job`, `fsm_service_visit`, `fsm_material_action` | Link/Select | Service Job, Service Visit, guarded material action |
| Stock Entry Detail    | `fsm_installed_equipment`                                     | Link        | Installed Equipment                                 |
| Delivery Note         | `fsm_service_job`                                             | Link        | Service Job                                         |

The extra rows are post-baseline Phase 6 correlations. They do not store stock balances or duplicate native state.

## Post-baseline Phase 7 root

`Failure Analysis` is an FSM diagnostic root owned by Quality/RCA and correlated to Service Job, Service Visit,
Installed Equipment and Equipment Inspection. It is not an additional work-order aggregate.

## Post-baseline Phase 8 evolution

The existing `Service Return` root was extended into the canonical pickup/RMA/workshop case. No `Repair Order`
DocType was added. ERPNext Quotation, Sales Invoice and Stock Entry remain authoritative for estimate, billing and
stock respectively.

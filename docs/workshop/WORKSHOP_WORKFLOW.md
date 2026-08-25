# Workshop / RMA workflow

Date: 2026-08-25. Status: implemented.

`Service Return` is the canonical pickup, RMA and workshop case. A separate Repair Order was rejected because
`Service Job` remains the canonical work order. The case references one Job and optionally one Installed Equipment.

## Lifecycle

Draft → Pickup Requested → Picked Up → Workshop Received → Initial Inspection → Estimate Required → Awaiting
Customer Approval → Repair In Progress → Repair Completed → Testing → Quality Inspection → Ready for Dispatch →
Dispatched → Reinstalled → Closed. Repair may move to and from Waiting Material; any open state may be Cancelled
with a reason.

Server commands own transitions. Quotation is required before customer approval, explicit approval is required
before repair, repair/testing/QA evidence is required at the relevant gates, and a final outcome is required before
closure. Direct document creation and state editing are blocked.

## Ownership

- ERPNext Quotation owns the estimate and commercial approval reference.
- ERPNext Sales Invoice owns billing.
- ERPNext Stock Entry owns physical receipt and parts movements.
- Service Time Log owns labour evidence.
- Service Job owns the work order; Service Return owns custody and workshop lifecycle only.
- Installed Equipment owns the maintained unit identity and history correlation.

The compatibility `create_return` and `process_return` APIs route into this same aggregate; they are not a second
workflow. All clients consume the shared typed `WorkshopApi` contract.

## Security and audit

Every mutation authorizes the parent Job and validates company/equipment/document relations before any permission
bypass. Events `WorkshopCaseCreated`, `WorkshopCaseUpdated`, and `WorkshopCaseStatusChanged` are correlated to the
Job and equipment. Submitted Stock Entry remains the authoritative inventory record.

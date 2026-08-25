# ARCH-004 ERPNext Ownership Matrix

Status: **Binding target proposal**

| Business concept | Source of truth | FSM responsibility | Forbidden FSM duplicate |
|---|---|---|---|
| Customer identity/account | ERPNext Customer | Link and operational projection | FSM Customer master |
| Person/contact methods | Frappe Contact | Link and customer-scope resolution | FSM Contact |
| Service/site address | Frappe Address | Link plus visit snapshot where audit requires | FSM Address master |
| Product/service catalogue | ERPNext Item, Item Price, Price List | Select items and record operational usage intent | FSM Product/Part master or price list |
| Serialized equipment | ERPNext Serial No | Link from Job Equipment | Installed Base duplicate |
| Capital equipment | ERPNext Asset | Optional link from Job Equipment | FSM Asset register |
| Warehouse and van location | ERPNext Warehouse | Link technician/crew van warehouse | Van Inventory master |
| Stock balance | ERPNext Bin/Stock Ledger Entry | Read projection only | FSM quantity-on-hand ledger |
| Parts demand | ERPNext Material Request | Command creation and link to Job | Spare Request with procurement state |
| Stock movement | ERPNext Stock Entry | Command creation and link to Job/Return | FSM issue/receipt transaction |
| Delivery | ERPNext Delivery Note | Link and show projection | FSM delivery/challan document |
| Estimate/offer | ERPNext Quotation | Create/link through authorized adapter | Service Estimate |
| Customer order | ERPNext Sales Order when applicable | Link to Job | FSM order |
| Billing | ERPNext Sales Invoice | Create/link and show status/outstanding | Service Billing/FSM Invoice |
| Credit/return accounting | ERPNext Sales Invoice return / Credit Note | Link from operational return outcome | FSM Credit Note |
| Collection | ERPNext Payment Entry | Read allocation/status and link | Bill Payment/FSM Receipt |
| Taxes, discounts, GL | ERPNext Accounts | Never calculate authoritative posting separately | FSM tax/payment ledger |
| Warranty basis | ERPNext Item/Serial No/Asset warranty data where available | Evaluate service entitlement and snapshot result | Competing warranty master |
| Service contract operational terms | FSM Service Contract | Own service period, covered scope, SLA and visit entitlements | ERPNext sales/accounting duplicate inside FSM |
| Contract quotation/order/invoice | ERPNext Quotation/Sales Order/Sales Invoice | Store validated links and use them as commercial truth | FSM quotation, order, invoice or payment document |
| Operational request | FSM Service Request | Own intake/triage/conversion | ERPNext Issue only if selected later as the canonical request; never both |
| Operational job | FSM Service Job | Canonical aggregate | Repair Order/work order duplicate |
| Visit execution | FSM Service Visit | Own attendance evidence | ERPNext billing/stock state |
| Technician operational profile | FSM Technician linked to User/Employee | Skills, duty, dispatch state | Duplicate User/Employee identity |
| Maintenance recurrence | FSM only if ADR-007 overlap decision is approved | Plan/occurrence idempotency | Duplicate execution Job or ERP accounting |

## Integration invariant

FSM stores only foreign keys, immutable operational snapshots needed for audit, and projection timestamps. It must not mirror ERPNext monetary totals or stock status as independently editable truth. Reconciliation always prefers the ERPNext document and ledger.

## Current conflicts

- `Service Job.total_amount` and cost fields are operational estimates, not authoritative invoice totals; labels and APIs must make this distinction explicit.
- Current invoice creation bypasses Sales Invoice permission and needs an authorized command adapter.
- Current return receipt bypasses Stock Entry permission and directly submits; target must separate FSM approval from ERPNext posting authorization.
- Current analytics calls completed-job amount “revenue”; revenue must come from submitted ERPNext Sales Invoices/GL, not Service Job totals.

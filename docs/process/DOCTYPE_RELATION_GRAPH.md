# DocType relation graph

```text
ERPNext Customer ─┬─ Customer Site ─ Equipment Location
                  ├─ Installed Equipment ← ERPNext Delivery Note
                  ├─ Service Contract ─┬─ Coverage / Entitlements
                  │                    └─ Maintenance Plan ─ Occurrence
                  └─ Service Request ─────────────────────────────┐
ERPNext Project (optional grouping) ──────────────────────────────┤
                                                                 v
                    Service Job (canonical aggregate)
                    ├─ Service Job Equipment ─ Installed Equipment
                    ├─ Service Visit ─ Team / Technician
                    ├─ Equipment Inspection ─ Failure Analysis
                    ├─ Service Job Item ─ ERPNext stock documents
                    ├─ Service Return ─ workshop lifecycle
                    ├─ Service Report ─ Service Certificate
                    └─ ERPNext Quotation / Sales Invoice
```

Child tables are aggregate-owned and have no independent navigation. ERPNext Project is a reference on Contract, Plan, Request, Job, Visit, Occurrence and Report; it is deliberately absent from Customer Site and Installed Equipment ownership.

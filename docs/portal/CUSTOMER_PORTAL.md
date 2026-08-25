# Customer portal completion

Date: 2026-08-25. Status: implemented.

The authenticated dashboard provides customer-owned Sites, Equipment, upcoming/overdue maintenance, Requests,
active Job tracking, service history, Reports, Certificates, Contracts, renewal quotations, Quotations, Invoices
and feedback through the existing Job tracking flow.

`get_my_portal_hub` resolves the Customer from the signed-in Contact and fixes all fields server-side. Native
Quotation and Sales Invoice reads are restricted to Service Jobs already proven to belong to that Customer. The
projection intentionally excludes labour/material/travel/total cost, warehouse/stock quantities, internal notes,
staff-private data and every other Customer's records.

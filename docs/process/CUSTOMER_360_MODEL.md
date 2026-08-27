# Customer 360 model

`get_customer_360` provides one company-scoped projection over the ERPNext Customer plus Sites, Equipment, Contracts, Maintenance Plans, Requests, Jobs, Quotations and Sales Invoices. It is navigation/read context only; each source record keeps ownership and permissions.

Site 360 remains `get_customer_site` plus equipment locations, jobs and requests. Equipment 360 remains `get_equipment` and `get_equipment_history`, backed by Service Event Log and linked Job Equipment rows.

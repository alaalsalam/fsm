# Corrective service flow

`Portal/Console Request → triage → coverage → Job → Team → Visit → diagnosis/inspection → on-site fix | material wait | workshop | replacement → report → ERPNext quotation/invoice when chargeable → completion → equipment history`.

Request, Job and Visit statuses remain independently owned. Conversion is one-to-many with an idempotency key; downstream commercial and stock records remain ERPNext-owned.

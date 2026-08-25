# Reports and certificates

Date: 2026-08-25. Status: implemented.

`Service Report` is the approved operational snapshot for one canonical Service Job. It captures customer/site,
visits, team, equipment, inspections, failures, native ERPNext material documents, workshop outcomes, work and
recommendations as versioned JSON. Supported report types are Service, Inspection and Preventive Maintenance.

Lifecycle is Draft → Generated → Customer Review → Customer Signed → Verified → Submitted. Customer signature or
an explicit refusal plus reason is mandatory. Manager verification/submission is mandatory. Submitted records are
immutable; revision creates N+1 and links `supersedes` while preserving prior evidence.

`Service Certificate` is issued only from a Submitted report. Refill and Hydro Test types are implemented. It
retains the approved snapshot, optional equipment scope, revision and issue/revocation audit. Generation keys make
report and certificate retries idempotent.

All commands authorize the parent Job. Customer/company/technician visibility therefore follows the same canonical
scope. Console, Portal and Mobile share `ReportingApi`; dedicated presentation is completed in their later phases.

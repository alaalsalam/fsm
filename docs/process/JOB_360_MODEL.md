# Job 360 model

`get_job_hub` returns the canonical Job plus Next Action, structured completion blockers, Visits, Inspections, Failures, Workshop cases, Reports and Certificates. Existing logistics, costing, coverage and commercial APIs supply the remaining tabs.

The Job owns work-order state only. Visit owns execution, Inspection owns equipment outcome, Workshop owns repair state, Report owns report state and ERPNext owns financial/stock state.

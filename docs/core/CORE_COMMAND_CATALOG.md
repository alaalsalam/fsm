# CORE command catalogue

Every command authorizes before mutation and returns the refreshed document projection.

| Aggregate | Command/API | Actor and principal guard | Result |
|---|---|---|---|
| Request | `open_request` | in-scope Manager | Draft→Open |
| Request | `triage_request` | in-scope Manager | Open→Triaged |
| Request | `cancel_request` | in-scope Manager | active→Cancelled |
| Request | `close_request` | in-scope Manager | Open/Triaged/Converted→Closed |
| Request→Job | `create_job_from_request` | in-scope Manager; status + unique idempotency key | creates one canonical Job per operation key; Request→Converted |
| Job | `plan_job` | in-scope Manager | Draft→Planned |
| Job | `schedule_job` | in-scope Manager; valid time window | Planned→Scheduled |
| Job | `dispatch_job` | in-scope Manager; active same-company technician | Scheduled→Dispatched |
| Job | `start_job` | assigned technician or in-scope Manager | Scheduled/Dispatched→In Progress |
| Job | `hold_job` | assigned technician or in-scope Manager; reason allowlist | active→On Hold |
| Job | `resume_job` | assigned technician or in-scope Manager | On Hold→recorded active state |
| Job | `cancel_job` | in-scope Manager | non-terminal→Cancelled |
| Job | `complete_job` | assigned technician or in-scope Manager; CompletionPolicy | In Progress→Completed |
| Visit | `create_visit` | in-scope Manager; active Job, valid technician/window | creates Planned Visit |
| Visit | `dispatch_visit` | in-scope Manager; technician required | Planned→Dispatched |
| Visit | `start_travel` | assigned technician/in-scope Manager | Dispatched→En Route |
| Visit | `check_in_visit` | assigned technician/in-scope Manager; coordinate validation | En Route→Checked In |
| Visit | `start_visit_work` | assigned technician/in-scope Manager | Checked In→In Progress; eligible Job starts |
| Visit | `check_out_visit` | assigned technician/in-scope Manager; coordinate validation | In Progress→Checked Out |
| Visit | `complete_visit` | assigned technician/in-scope Manager | Checked Out→Completed; Job remains open |
| Visit | `cancel_visit` | assigned technician/in-scope Manager | non-terminal→Cancelled |

Read projections are `list_service_requests`, `get_service_request`, `get_job_visits`, `get_service_visit`, and `get_service_timeline`. Public intake is `fsm.api.request_service`; `book_appointment` is a deprecated forwarding alias only.

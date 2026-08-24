# Permission test matrix

| Actor/scenario | Positive assertion | Negative assertion | Automated evidence |
|---|---|---|---|
| System Manager | setup and administrative scope remains available | Guest cannot invoke authenticated APIs | `test_guest_endpoints_are_explicit` plus FSM controller tests |
| FSM Manager Company A | lists/KPIs include Company A Job | cannot read Company B Job or aggregate its counts | `test_manager_cannot_cross_company_scope`, `test_dashboard_respects_company_scope` |
| FSM Manager Company B | independent fixture and User Permission | Company A root denied by same policy | symmetric fixture exercised by Company A negative root |
| Technician A | reads and completes assigned Job A | cannot complete or read Job B | `test_technician_can_only_read_and_mutate_assigned_job` |
| Technician B | may act only on Job B | cannot create a child message against Job A | `test_child_document_cannot_bypass_root_permission` |
| Customer A | reads own Jobs/Appointments, posts own message/feedback, and reads own detail | cannot read Customer B Job/messages | `test_customer_can_only_read_owned_records` |
| Customer B | independent Contact→Customer fixture | Customer A ownership comparison cannot be bypassed by name | symmetric fixture and Customer A negative calls |
| Guest | session projection is explicitly public | dispatch list requires authentication | `test_guest_endpoints_are_explicit` |
| Registration required fields | fixed fields accepted | missing fields rejected | `test_missing_fields` |
| Registration duplicate | unique account accepted once | existing User and duplicate retry rejected | `test_existing_user`, `test_successful_registration_and_duplicate_retry` |
| Registration linkage | Website User gets only FSM Customer and linked Contact/Customer | arbitrary user type/roles are not accepted parameters | `test_successful_registration_and_duplicate_retry` |
| Registration atomicity | successful three-record transaction | Contact failure rolls back User and Customer | `test_registration_rolls_back_on_contact_failure` |
| Existing Job controller behavior | checklist and totals remain functional | invalid sequence/state remains guarded | `TestServiceJob` tests plus transition guards |
| Frontend enforcement | Console and Portal redirect anonymous protected routes | failed API/session does not become authenticated | Console/Portal Vitest and Playwright smoke tests |

Backend result on clean `digit16-gate.localhost`: **13 passed**. Frontend: **10 unit tests passed** and **6 E2E tests passed** at 390×844 and 1440×900.

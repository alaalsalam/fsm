# API authorization matrix

Date: 2026-08-24. Inventory source: Python whitelist decorators at the CORE closeout revision. Total: **85/85 current endpoints classified**. The original 58-row GATE-001 table remains below as an audit baseline; two removed document RPCs and all 29 CORE additions are reconciled in the CORE delta. Default is deny; frontend visibility is never an authorization control.

Legend: access `G` = explicit Guest, `A` = authenticated. Scope columns use `C` = Company User Permission, `T` = Service Territory, `O` = current Customer ownership, `A` = assigned Technician, `—` = not applicable. Read/bypass values are `No`, `Scoped` (root IDs or warehouses were authorized first), or the named documented exception. Tests: `AUTH`, `COMP`, `CUST`, `TECH`, `GUEST`, `FIELDS`, `STATE`, `AGG`, `RATE`, `ROLLBACK`, `CHILD`, `E2E`.

| # | Endpoint | Access; actor → action | Root resource | Required role | C | T | O | Tech | Accepted input fields | Permission function | `get_all` | `ignore_permissions` | Residual risk | Required tests |
|---:|---|---|---|---|:---:|:---:|:---:|:---:|---|---|---|---|---|---|
| 1 | `fsm.api.get_dispatch_jobs` | A; Manager/Technician/Customer → list visible Jobs | Service Job | FSM role/System Manager | C | T* | O | A | `status, technician, limit≤200` | query hook + `require_authenticated` | No | No | Low | AUTH,COMP,CUST,TECH,E2E |
| 2 | `fsm.api.get_dashboard_stats` | A; FSM actors → scoped KPIs | Service Job | FSM role/System Manager | C | T* | O | A | none | query hook + `require_authenticated` | No | No | Low | COMP,CUST,TECH,AGG |
| 3 | `fsm.api.create_invoice_from_job` | A; Manager → draft invoice | Service Job | FSM Manager/System Manager | C | T | — | — | `job` | `require_job_access(write, manager_only)` | No | No for HTTP path | Medium: accounting command | AUTH,COMP,FIELDS |
| 4 | `fsm.api.start_job_task` | A; assigned Technician/Manager → transition task | Service Job | Technician/Manager/System Manager | C | T | — | A | `job, idx` | `require_job_access(write)` + state guard | No | Conditional system auto-invoice only | Low | TECH,COMP,STATE |
| 5 | `fsm.api.complete_job_task` | A; assigned Technician/Manager → transition task | Service Job | Technician/Manager/System Manager | C | T | — | A | `job, idx, note` | `require_job_access(write)` + sequence guard | No | Conditional system auto-invoice only | Low | TECH,COMP,STATE,FIELDS |
| 6 | `fsm.api.complete_job` | A; assigned Technician/Manager → canonical completion command | Service Job | Technician/Manager/System Manager | C | T | — | A | `job` | forwards to `service_operations.commands.complete_job`; CompletionPolicy | No | Conditional system auto-invoice only | Medium: invoice side effect | TECH,COMP,STATE |
| 7 | `fsm.api.register_customer` | G; Guest → create fixed Website User/Customer/Contact | registration aggregate | Guest | — | — | self | — | `full_name,email,password,phone` only | allowlist + validation + fixed role/type + rate limit | No | Approved guest bootstrap | Medium: public identity creation | GUEST,FIELDS,RATE,ROLLBACK,CUST |
| 8 | `fsm.api.get_portal_session` | G; Guest/auth user → session projection | User/Contact | Guest | — | — | O | — | none | explicit Guest branch + `current_customer(optional)` | No | No | Low | GUEST,CUST,E2E |
| 9 | `fsm.api.get_my_appointments` | A; Customer → own Requests | Service Request | FSM Customer | C* | T* | O | — | none | deprecated alias to `get_my_requests` | No | No | Low; removal requires client window | AUTH,CUST |
| 10 | `fsm.api.get_my_jobs` | A; Customer → own Jobs | Service Job | FSM Customer | C* | T* | O | — | none | `current_customer` + Job query hook | No | No | Low | AUTH,CUST |
| 11 | `fsm.api.get_my_job` | A; Customer → own Job detail | Service Job | FSM Customer | C* | T* | O | — | `job` | explicit owner comparison | No | No | Low | CUST,FIELDS |
| 12 | `fsm.api.book_appointment` | G; Guest/Customer → Request intake | Service Request | Guest | default | — | optional O | — | same fixed allowlist as `request_service` | deprecated alias; public intake guard + rate limit | No | Approved Request insert | Medium: public write/abuse | GUEST,FIELDS,RATE |
| 13 | `fsm.scheduling.suggest_technicians` | A; Manager → ranked candidates | Service Job | FSM Manager/System Manager | C | T | — | — | `job, limit≤50` | `require_job_access(read, manager_only)` | Scoped child skills | No | Low | AUTH,COMP,AGG |
| 14 | `fsm.scheduling.assign_technician` | A; Manager → assignment | Service Job | FSM Manager/System Manager | C | T | — | — | `job, technician` | `require_job_access(write, manager_only)` + same-company guard | Scoped child skills | No | Low | COMP,STATE,FIELDS |
| 15 | `fsm.scheduling.get_available_technicians` | A; Manager → workforce search | Company | FSM Manager/System Manager | C | T | — | — | `territory,service_type,scheduled_date,company` | `resolve_manager_company` + `require_manager_scope` | Scoped child skills | No | Low | COMP,AUTH,FIELDS |
| 16 | `fsm.tracking.update_location` | A; Technician → append GPS | Service Job when supplied | FSM Technician | C* | T* | — | A | `latitude,longitude,accuracy,job` | current technician + `require_technician_assignment` | No | Authorized append-only location log | Medium: precise location | AUTH,TECH,CHILD,FIELDS |
| 17 | `fsm.tracking.clock_in` | A; Technician → duty state | Technician | FSM Technician | profile | — | — | self | none | current technician identity | No | No | Low | AUTH,TECH |
| 18 | `fsm.tracking.clock_out` | A; Technician → duty state | Technician | FSM Technician | profile | — | — | self | none | current technician identity | No | No | Low | AUTH,TECH |
| 19 | `fsm.tracking.nearest_technicians` | A; Manager → proximity list | Service Job | FSM Manager/System Manager | C | T | — | — | `job, limit≤50` | `require_job_access(read, manager_only)` + manager scope | No | No | Medium: location projection | COMP,AUTH,FIELDS |
| 20 | `fsm.costing.start_timer` | A; Technician → append time | Service Job | FSM Technician | C* | T* | — | A | `job,activity` | current technician + assignment guard | No | No | Low | TECH,CHILD,FIELDS |
| 21 | `fsm.costing.stop_timer` | A; Technician → close own timer | Service Job | FSM Technician | C* | T* | — | A | `job` | current technician + assignment guard + own open log | Scoped by Job/Technician | No | Low | TECH,STATE |
| 22 | `fsm.costing.estimate_job` | A; Manager → historical estimate | Company/Service Job | FSM Manager/System Manager | C | — | — | — | `service_type,technician` | `resolve_manager_company` + manager scope | No | No | Low | COMP,AGG,FIELDS |
| 23 | `fsm.costing.get_job_cost_summary` | A; Manager → cost projection | Service Job | FSM Manager/System Manager | C | T | — | — | `job` | `require_job_access(read, manager_only)` | Scoped time logs | No | Medium: cost data | COMP,AGG |
| 24 | `fsm.inventory.get_stock_levels` | A; Manager/Technician → stock projection | Warehouse/Technician | Manager/Technician/System Manager | C | — | — | self for tech | `warehouse,technician,item,low_only` | role + own van/company warehouse guard | Scoped warehouses/items | No | Medium: inventory quantities | AUTH,COMP,TECH,AGG |
| 25 | `fsm.inventory.get_van_stock` | A; Technician/Manager → van stock | Technician/Warehouse | Manager/Technician/System Manager | C | — | — | self or manager | `technician` | role/self resolution then `get_stock_levels` | Scoped warehouses/items | No | Low | TECH,COMP |
| 26 | `fsm.logistics.request_parts` | A; assigned actor → Material Request | Service Job | Technician/Manager/System Manager | C | T | — | A | `job,items,required_by,warehouse` fixed item keys | `require_job_access(write)` + item allowlist | No | Authorized ERPNext child operation | Medium: stock request | TECH,COMP,FIELDS |
| 27 | `fsm.logistics.get_job_logistics` | A; visible actor → logistics timeline | Service Job | FSM role/System Manager | C | T | O | A | `job` | `require_job_access(read)` | No | No | Low | CUST,TECH,COMP |
| 28 | `fsm.returns.create_return` | A; visible actor → request return | Service Job | Technician/Manager/System Manager | C | T | — | A | `service_job,items,warehouse,reason` fixed item keys | `require_job_access(write)` + item allowlist | No | No | Medium: return data | TECH,COMP,FIELDS |
| 29 | `fsm.returns.list_returns` | A; FSM actor → scoped returns | Service Return→Job | FSM role/System Manager | C | T* | O* | A | `status,job` | child query hook + authenticated | No | No | Low | AUTH,COMP,TECH |
| 30 | `fsm.returns.get_return` | A; visible actor → return detail | Service Return→Job | FSM role/System Manager | C | T | O* | A | `name` | `require_job_access(read)` | No | No | Low | COMP,TECH,FIELDS |
| 31 | `fsm.returns.process_return` | A; Manager → transition return | Service Return→Job | FSM Manager/System Manager | C | T | — | — | `name,action∈approve/receive/close` | `require_job_access(write, manager_only)` + state guard | No | Receipt exception on receive | Medium: stock posting | COMP,STATE,FIELDS |
| 32 | `fsm.messaging.get_messages` | A; visible actor → thread | Service Job | FSM role/System Manager | C | T | O | A | `job` | `require_job_access(read)` + child query hook | No | No | Low | CUST,TECH,COMP |
| 33 | `fsm.messaging.post_message` | A; visible actor → append message | Service Job | FSM role/System Manager | C | T | O | A | `job,message`; caller role ignored/inferred | `require_job_access(read)` + child permission | No | No | Low | CUST,TECH,FIELDS,CHILD |
| 34 | `fsm.feedback.submit_feedback` | A; Customer → create feedback | Service Job | FSM Customer | C* | T* | O | — | `job,rating,comments,nps_score` | `require_job_access(read)` + customer identity | No | No | Low | CUST,FIELDS,CHILD |
| 35 | `fsm.feedback.get_feedback` | A; visible actor → feedback | Service Job | FSM role/System Manager | C | T | O | A | `job` | `require_job_access(read)` | No | No | Low | CUST,TECH,COMP |
| 36 | `fsm.feedback.get_csat_summary` | A; Manager → aggregate | Company/Service Job | FSM Manager/System Manager | C | — | — | — | `days` bounded | manager company scope + scoped Jobs | No | No | Low | COMP,AGG,FIELDS |
| 37 | `fsm.customers.get_customer_profile` | A; staff → customer projection | Customer via visible Jobs | Manager/Technician/System Manager | C | T* | — | A* | `customer` | `require_customer_access` via scoped Job | No | No | Medium: PII | COMP,TECH,FIELDS |
| 38 | `fsm.customers.add_field_note` | A; Technician → append note | Service Job/Customer | FSM Technician | C* | T* | — | A | `customer,note,job`; Job customer must match | technician + assignment/root relation guard | No | No | Medium: customer notes | TECH,CHILD,FIELDS |
| 39 | `fsm.customers.list_field_notes` | A; staff → notes | Customer via visible Jobs | Manager/Technician/System Manager | C | T* | — | A* | `customer` | `require_customer_access` + child query hook | No | No | Medium: PII | COMP,TECH |
| 40 | `fsm.contractors.list_subcontractors` | A; Manager → partner list | Subcontractor | FSM Manager/System Manager | C | — | — | — | `status` | role + resolved company | No | No | Low | AUTH,COMP |
| 41 | `fsm.contractors.get_subcontractor_work` | A; Manager → partner performance | Subcontractor/Service Job | FSM Manager/System Manager | C | — | — | — | `subcontractor` | role + subcontractor company scope | No | No | Low | COMP,AGG |
| 42 | `fsm.analytics.service_performance` | A; Manager → KPI aggregate | Company/Service Job | FSM Manager/System Manager | C | — | — | — | `days` bounded | manager company + scoped Job list | No | No | Low | COMP,AGG |
| 43 | `fsm.analytics.workorder_volume` | A; Manager → volume aggregate | Company/Service Job | FSM Manager/System Manager | C | — | — | — | `days` bounded | manager company + scoped Job list | No | No | Low | COMP,AGG |
| 44 | `fsm.analytics.inventory_usage` | A; Manager → item aggregate | Company/Service Job | FSM Manager/System Manager | C | — | — | — | `days,limit` bounded | scoped Job IDs before child read | Scoped Job children | No | Low | COMP,AGG,FIELDS |
| 45 | `fsm.analytics.technician_utilization` | A; Manager → workforce aggregate | Company/Service Job | FSM Manager/System Manager | C | — | — | — | `days` bounded | manager company + scoped Jobs/Technicians | No | No | Low | COMP,AGG |
| 46 | `fsm.integrations.generate_api_keys` | A; administrator → credential issue | User | System Manager | — | — | — | — | `user` | `_require_admin` | No | No | High: secret shown once | AUTH,FIELDS |
| 47 | `fsm.integrations.create_job` | A token/cookie; Manager → Job creation | Company/Customer | FSM Manager/System Manager | C | T | — | — | fixed job fields + fixed item keys | role + company/territory + item allowlist | No | No | Medium: integration write | AUTH,COMP,FIELDS |
| 48 | `fsm.integrations.get_job_status` | A token/cookie; Manager → status projection | Service Job | FSM Manager/System Manager | C | T | — | — | `job` | `require_job_access(read, manager_only)` | No | No | Low | AUTH,COMP |
| 49 | `fsm.integrations.list_jobs` | A token/cookie; Manager → Job projection | Company/Service Job | FSM Manager/System Manager | C | — | — | — | `status,customer,limit≤200` | role + resolved company + query hook | No | No | Low | AUTH,COMP,FIELDS |
| 50 | `fsm.integrations.register_webhook` | A; administrator → Webhook creation | Webhook | System Manager | — | — | — | — | `request_url,docevent` | `_require_admin` | No | Authorized administrator bypass | High: outbound destination | AUTH,FIELDS |
| 51 | `fsm.integrations.list_webhooks` | A; administrator → Webhook list | Webhook | System Manager | — | — | — | — | none | `_require_admin` | No | No | Medium: integration metadata | AUTH |
| 52 | `ServiceJob.start_task` | A document RPC; assigned actor → task transition | Service Job | Technician/Manager/System Manager | C | T | — | A | `idx` | `require_job_access(write)` + sequence guard | No | Conditional system auto-invoice only | Low | TECH,COMP,STATE |
| 53 | `ServiceJob.complete_task` | A document RPC; assigned actor → task transition | Service Job | Technician/Manager/System Manager | C | T | — | A | `idx,note` | `require_job_access(write)` + sequence guard | No | Conditional system auto-invoice only | Low | TECH,COMP,STATE |
| 54 | `ServiceJob.complete_job` | **Removed in CORE**; replaced by canonical command | Service Job | — | — | — | — | — | — | no longer whitelisted | No | No | Closed duplicate lifecycle path | STATE |
| 55 | `ServiceAppointment.create_service_job` | **Removed in CORE** with Appointment controller | Service Appointment | — | — | — | — | — | — | replaced by Request command/RPC | No | No | Closed duplicate concept | STATE |
| 56 | `ServiceReturn.approve` | A document RPC; Manager → approve | Service Return→Job | FSM Manager/System Manager | C | T | — | — | document name only | `require_job_access(write, manager_only)` + state guard | No | No | Low | COMP,STATE |
| 57 | `ServiceReturn.receive` | A document RPC; Manager → receive/post stock | Service Return→Job | FSM Manager/System Manager | C | T | — | — | document name only | `require_job_access(write, manager_only)` + state guard | No | Authorized Stock Entry receipt | High: submitted stock document | COMP,STATE |
| 58 | `ServiceReturn.close` | A document RPC; Manager → close | Service Return→Job | FSM Manager/System Manager | C | T | — | — | document name only | `require_job_access(write, manager_only)` + state guard | No | No | Low | COMP,STATE |

## CORE endpoint delta (29 additions)

| Endpoint | Access and accepted input | Root guard/scope | Bypass decision |
|---|---|---|---|
| `fsm.api.get_my_requests` | A Customer; no input | `current_customer`; explicit Customer filter plus Request query hook | none |
| `fsm.api.request_service` | G; fixed `customer_name,contact_phone,service_address,service_type,preferred_date,notes` | POST rate limit, required fields, fixed default company, linked current Customer only | approved narrow Request insert |
| `open_request` | A scoped Manager; `request,source,correlation_id` | `_request_access(manager_only)` company/territory then transition map | event insert only |
| `triage_request` | same | same | event insert only |
| `cancel_request` | same | same | event insert only |
| `close_request` | same | same | event insert only |
| `create_job_from_request` | A scoped Manager; `request,idempotency_key,source` | Request scope/status; key 1–128; unique operation key | approved Job + event inserts after guard |
| `plan_job` | A scoped Manager; `job,source,correlation_id` | `require_job_access(write, manager_only)` + transition map | event insert only |
| `schedule_job` | A scoped Manager; plus start/end | same; valid time window | event insert only |
| `dispatch_job` | A scoped Manager; optional technician | same; active same-company Technician | event insert only |
| `start_job` | A assigned Technician/scoped Manager | `require_job_access(write)` + transition map | event insert only |
| `hold_job` | same; fixed reason allowlist | same | event insert only |
| `resume_job` | same | same; prior state allowlist | event insert only |
| `cancel_job` | A scoped Manager | manager-only Job access | event insert only |
| `complete_job` | A assigned Technician/scoped Manager | Job access + CompletionPolicy + active Visit rejection | event insert only |
| `create_visit` | A scoped Manager; Job/window/technician | manager Job scope; active Job; active same-company Technician | approved Visit + event inserts after guard |
| `dispatch_visit` | A scoped Manager | parent Job scope + technician present | event insert only |
| `start_travel` | A exact assigned Technician/scoped Manager | parent Job access + exact Visit assignment | event insert only |
| `check_in_visit` | same; coordinates/accuracy | same + coordinate validation | event insert only |
| `start_visit_work` | same | same + transition map | event insert only |
| `check_out_visit` | same; coordinates/accuracy | same + coordinate validation | event insert only |
| `complete_visit` | same | same + transition map | event insert only |
| `cancel_visit` | same | same + transition map | event insert only |
| `list_service_requests` | A; `status,limit≤200` | authenticated + Request permission query hook | none |
| `get_service_request` | A; `request` | Manager scope or Customer ownership; linked Jobs use permission query hook | none |
| `get_job_visits` | A; `job` | `require_job_access(read)` + Visit permission hook | none |
| `get_service_visit` | A; `visit` | parent Job read guard | none |
| `get_service_timeline` | A; fixed reference type/name | corresponding Request/Job/Visit read guard | none |
| `ServiceRequest.create_service_job` | A document RPC; optional idempotency key | forwards to manager-scoped canonical conversion command | same approved Job/event inserts |

The command names above are under `fsm.service_operations.commands`; read projections are under `fsm.service_operations.api`. `T*`, `C*`, `O*`, and `A*` mean scope inherited from the authorized root relation. Positive/negative CORE coverage is in `fsm.tests.test_service_operations`.

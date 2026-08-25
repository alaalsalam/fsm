# BASE-003 API Inventory

KodLyft FSM exposes 58 whitelisted methods: 51 module functions and 7 document methods. Frappe resource endpoints are also used by the shared TypeScript client. `Guest` is allowed only on the three methods explicitly marked below.

> This file preserves BASE-003 observations at the upstream baseline. GATE-001 closed the authorization findings; the authoritative post-hardening classification for all 58 endpoints is `docs/security/API_AUTHORIZATION_MATRIX.md`.

## Module APIs

| Module             | Method                      | Surface / purpose                  | Access observation                                                           |
| ------------------ | --------------------------- | ---------------------------------- | ---------------------------------------------------------------------------- |
| `fsm.api`          | `get_dispatch_jobs`         | Console/Mobile dispatch list       | Authenticated; permission-aware `get_list`                                   |
|                    | `get_dashboard_stats`       | Console KPI summary                | Authenticated; uses unrestricted counts/get_all                              |
|                    | `create_invoice_from_job`   | Create draft ERPNext Sales Invoice | Authenticated; permission bypass in helper                                   |
|                    | `start_job_task`            | Start checklist step               | Authenticated; document save checks apply                                    |
|                    | `complete_job_task`         | Complete checklist step            | Authenticated; document save checks apply                                    |
|                    | `complete_job`              | Complete job                       | Authenticated; document save checks apply                                    |
|                    | `register_customer`         | Portal self-registration           | **Guest**; creates User/Customer/Contact with bypass                         |
|                    | `get_portal_session`        | Portal session identity            | **Guest**, read-only                                                         |
|                    | `get_my_appointments`       | Customer appointment history       | Authenticated; explicit current-customer scope                               |
|                    | `get_my_jobs`               | Customer job history               | Authenticated; explicit current-customer scope                               |
|                    | `get_my_job`                | Customer job detail                | Authenticated; explicit ownership comparison                                 |
|                    | `book_appointment`          | Public booking                     | **Guest**; creates Service Appointment with bypass                           |
| `fsm.scheduling`   | `suggest_technicians`       | Candidate scoring                  | Authenticated; no role guard                                                 |
|                    | `assign_technician`         | Assignment mutation                | Authenticated; relies on Service Job write permission                        |
|                    | `get_available_technicians` | New-job technician search          | Authenticated; unrestricted workforce query                                  |
| `fsm.tracking`     | `update_location`           | Mobile GPS ping                    | Technician identity guard; supplied job not ownership-checked                |
|                    | `clock_in`                  | Mobile shift start                 | Technician identity guard                                                    |
|                    | `clock_out`                 | Mobile shift end                   | Technician identity guard                                                    |
|                    | `nearest_technicians`       | Dispatch proximity                 | Authenticated; no manager-role guard                                         |
| `fsm.costing`      | `start_timer`               | Start technician timer             | Technician identity guard; job assignment not checked                        |
|                    | `stop_timer`                | Stop technician timer              | Technician identity guard; bypass save                                       |
|                    | `estimate_job`              | Historical estimate                | Authenticated; unrestricted aggregate                                        |
|                    | `get_job_cost_summary`      | Console job costs                  | Authenticated; `get_doc` permission is not explicitly asserted               |
| `fsm.inventory`    | `get_stock_levels`          | Console stock view                 | Authenticated; ERPNext Bin query via `get_all`                               |
|                    | `get_van_stock`             | Mobile van stock                   | Authenticated; user-to-technician resolution only when no parameter supplied |
| `fsm.logistics`    | `request_parts`             | Create Material Request            | Authenticated; bypass insert, no explicit job authorization                  |
|                    | `get_job_logistics`         | Job MR/DN timeline                 | Authenticated; unrestricted queries                                          |
| `fsm.returns`      | `create_return`             | Open return                        | Authenticated; normal insert/save                                            |
|                    | `list_returns`              | Return list                        | Authenticated; unrestricted query                                            |
|                    | `get_return`                | Return detail                      | Authenticated; no explicit read assertion                                    |
|                    | `process_return`            | Approve/receive/close              | Authenticated; relies on document save permissions                           |
| `fsm.messaging`    | `get_messages`              | Job thread                         | Explicit staff/customer ownership guard                                      |
|                    | `post_message`              | Add job message                    | Explicit job access guard, then bypass insert                                |
| `fsm.feedback`     | `submit_feedback`           | Customer feedback                  | Explicit job/customer guard expected; bypass insert                          |
|                    | `get_feedback`              | Feedback detail                    | Authenticated; scope must remain verified                                    |
|                    | `get_csat_summary`          | Console CSAT/NPS                   | Authenticated; unrestricted aggregate                                        |
| `fsm.customers`    | `get_customer_profile`      | Console customer 360               | Authenticated; no manager/technician scope guard                             |
|                    | `add_field_note`            | Technician note                    | Technician identity guard; customer/job relationship needs validation        |
|                    | `list_field_notes`          | Customer notes                     | Authenticated; unrestricted query                                            |
| `fsm.contractors`  | `list_subcontractors`       | Partner list                       | Authenticated; unrestricted query                                            |
|                    | `get_subcontractor_work`    | Partner performance                | Authenticated; unrestricted query                                            |
| `fsm.analytics`    | `service_performance`       | Service KPI aggregate              | Authenticated; `get_all` bypasses user permissions                           |
|                    | `workorder_volume`          | Work volume aggregate              | Authenticated; `get_all` bypasses user permissions                           |
|                    | `inventory_usage`           | Parts consumption aggregate        | Authenticated; `get_all` bypasses user permissions                           |
|                    | `technician_utilization`    | Workforce aggregate                | Authenticated; `get_all` bypasses user permissions                           |
| `fsm.integrations` | `generate_api_keys`         | Generate API credentials           | Explicit System Manager guard                                                |
|                    | `create_job`                | External job creation              | Token-authenticated but no explicit FSM authorization guard                  |
|                    | `get_job_status`            | External status lookup             | Token-authenticated; scope not explicit                                      |
|                    | `list_jobs`                 | External job list                  | Token-authenticated; uses unrestricted query                                 |
|                    | `register_webhook`          | Create Webhook                     | Explicit admin guard expected in module                                      |
|                    | `list_webhooks`             | List Webhooks                      | Explicit admin guard expected in module                                      |

## Document methods

| DocType             | Method               | Transition/action                                  |
| ------------------- | -------------------- | -------------------------------------------------- |
| Service Job         | `start_task`         | Pending → In Progress, sequential guard            |
| Service Job         | `complete_task`      | In Progress/Pending → Done, sequential guard       |
| Service Job         | `complete_job`       | Job → Completed when checklist permits             |
| Service Appointment | `create_service_job` | Creates and links canonical Service Job            |
| Service Return      | `approve`            | Requested → Approved                               |
| Service Return      | `receive`            | Approved → Received and optional ERP stock receipt |
| Service Return      | `close`              | Received → Closed                                  |

## Scheduled tasks and realtime contracts

| Type     | Contract                                          |
| -------- | ------------------------------------------------- |
| Hourly   | `fsm.tasks.flag_sla_breaches`                     |
| Daily    | `fsm.tasks.notify_low_stock`                      |
| Realtime | `fsm_service_job_update` after Service Job update |
| Realtime | `fsm_technician_update` after Technician update   |

## Shared client contract

`frontend/api` provides one `FrappeClient` with cookie/CSRF authentication for web and token authentication for mobile, resource CRUD, whitelisted calls, uploads, and Socket.IO support. Console, Portal, and Mobile still define separate domain wrapper/type files; therefore transport is shared, but the domain contract is not yet a single generated or versioned source of truth.

## Integration points

| Integration               | Direction          | Current mechanism                                                            | Authority                        |
| ------------------------- | ------------------ | ---------------------------------------------------------------------------- | -------------------------------- |
| ERPNext Customer/Contact  | FSM → ERPNext      | Portal registration and appointment conversion create/link native records    | ERPNext/Frappe                   |
| ERPNext Item/UOM          | ERPNext → FSM      | Service Job/Return child rows link native masters                            | ERPNext Stock                    |
| ERPNext Warehouse/Bin     | ERPNext → FSM      | Technician van Warehouse and stock-level projections                         | ERPNext Stock                    |
| ERPNext Material Request  | FSM → ERPNext      | guarded shortage adapter; Job/Visit/Equipment correlations                   | ERPNext Stock                    |
| ERPNext Pick List         | FSM → ERPNext      | guarded operational reservation; Job/Visit/Equipment correlations            | ERPNext Stock                    |
| ERPNext Delivery Note     | ERPNext → FSM      | Job logistics projection; custom link `fsm_service_job`                      | ERPNext Stock                    |
| ERPNext Stock Entry       | FSM → ERPNext      | guarded transfer/issue/consume/return plus Service Return receipt             | ERPNext Stock                    |
| ERPNext Sales Invoice     | FSM → ERPNext      | Job items create/link a draft invoice                                        | ERPNext Accounts                 |
| Frappe Webhook/API keys   | External ↔ FSM     | Admin integration methods and token-authenticated job APIs                   | Frappe Integration               |
| Frappe realtime/Socket.IO | Server → clients   | Job, technician, and message events                                          | FSM projections                  |
| Capacitor device APIs     | Mobile → device    | Geolocation, camera, network, preferences, notifications, keyboard/status UI | Device platform                  |
| Google Fonts              | Web → external CDN | Console/Portal HTML preconnect and stylesheet                                | External presentation dependency |

No payment gateway integration, external map/ETA provider, email/SMS gateway adapter, or accounting synchronization outside native ERPNext documents is implemented in the KodLyft baseline.

## Post-baseline Phase 6 delta

`fsm.materials` adds four guarded methods: `get_material_plan`, `request_shortage`, `reserve_materials`, and
`post_material_movement`. They use ERPNext Bin, Material Request, Pick List and Stock Entry only. The legacy
`fsm.logistics.request_parts` endpoint is a compatibility alias to `request_shortage`, not a second implementation.
The shared `MaterialsApi` in `frontend/api` is the one typed consumer contract for all three surfaces.

Phase 7 adds six guarded RCA methods under `fsm.failure_analysis`: create, update, transition, explicitly apply
priority suggestion, list and get. `frontend/api` exposes the single typed `FailureAnalysisApi` contract.

## Contract gaps

- No API version prefix or compatibility policy.
- No OpenAPI/JSON Schema artifacts and no consumer-driven contract tests.
- Mutation methods do not consistently enforce explicit authorization before bypassing permissions.
- Multiple list/analytics methods use `get_all`, which ignores user permission filtering.
- Limit parameters are not uniformly bounded.
- Guest registration/booking lacks documented rate limiting, anti-abuse controls, and idempotency.
- Mobile token provisioning stores long-lived API key/secret credentials; ADR-009 requires a safer device session design.
## Post-baseline Phase 8 delta

Workshop/RMA extends the existing returns module with `create_workshop_case`, `update_workshop_case` and
`transition_workshop_case`; `create_return` and `process_return` remain compatibility paths into the same aggregate.
The shared `WorkshopApi` is the typed consumer contract. No generic CRUD endpoint or parallel Repair Order API was
introduced.

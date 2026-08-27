# API process map

| Flow | Read/projection APIs | Mutation owners |
|---|---|---|
| After-sales | `fsm.process.after_sales.get_after_sales_setup`, installed-base APIs | Delivery Note provisioning; installed-base commands |
| Contract → PM | contract/maintenance APIs, preview in `maintenance_flow` | `create_maintenance_plans_from_contract`, maintenance commands |
| Request → Job | service-operations APIs, `get_next_action` | service-operation command handlers |
| Job hub | `get_job_hub`, visits, logistics, reporting and commercial projections | domain command modules only |
| PM | maintenance list/summary APIs | generate/release/reschedule/skip commands |
| Workshop | returns projections | return/workshop commands |
| Completion | `completion_blockers` through job hub | `complete_job` plus CompletionPolicy |
| Operations | `get_operations_home`, `list_visits`, `list_exceptions`, `get_customer_360` | links to existing commands |

Every new whitelisted endpoint authenticates and enforces manager/company or Job authorization. UI code contains orchestration only at the presentation level and does not write through generic database APIs.

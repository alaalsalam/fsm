# BASE-004 Route Inventory

## Frappe website routes

| Public prefix | Frappe target | Authentication intent | Build source |
|---|---|---|---|
| `/fsm-console` | `fsm/www/fsm-console.html` | Staff session required inside SPA | Console Vite build |
| `/fsm-console/<path>` | `fsm-console` | Same | `website_route_rules` |
| `/book` | `fsm/www/book.html` | Public entry; account pages authenticate | Portal Vite build |
| `/book/<path>` | `book` | Same | `website_route_rules` |

Final runtime smoke test on `bench --site fsm-dev.localhost serve --port 8017 --noreload`: both base paths returned HTTP 200.

## Console routes

Base: `/fsm-console`

| SPA path | Name | View | Domain owner |
|---|---|---|---|
| `/login` | login | LoginView | Identity/Frappe |
| `/` | dispatch | DispatchBoardView | FSM Dispatch |
| `/jobs` | jobs | JobsView | FSM Operations |
| `/jobs/new` | job-new | NewJobView | FSM Operations |
| `/jobs/:name` | job-detail | JobDetailView | FSM Operations |
| `/inventory` | inventory | InventoryView | ERPNext Stock (FSM projection) |
| `/returns` | returns | ReturnsView | FSM Returns + ERPNext Stock |
| `/subcontractors` | subcontractors | SubcontractorsView | FSM Workforce |
| `/analytics` | analytics | AnalyticsView | FSM Analytics |
| `/integrations` | integrations | IntegrationsView | Platform Integration |
| `/account` | account | AccountView | Identity/Frappe |

## Portal routes

Base: `/book`

| SPA path | Name | View | Domain owner |
|---|---|---|---|
| `/` | book | BookingView | FSM Intake |
| `/signup` | signup | SignupView | Identity + ERPNext Customer |
| `/login` | login | LoginView | Identity/Frappe |
| `/account` | account | AccountView | FSM Customer Experience |
| `/track/:job` | track | TrackView | FSM Customer Experience |

## Mobile routes

| Native/web path | Name | View | Domain owner |
|---|---|---|---|
| `/` | redirect | Redirect to `/jobs` | FSM Mobile |
| `/jobs` | jobs | JobListView | FSM Work Execution |
| `/jobs/:id` | job-detail | JobDetailView | FSM Work Execution |

## Route gaps

- Console and Portal have independent router declarations; route metadata is not generated from a shared contract.
- Mobile has no login/settings/sync-conflict routes and no explicit offline recovery surface.
- Mobile job list contains hard-coded sample records in source, violating the live-data-only baseline.
- There is no route-level role policy shared with the backend; frontend guards are navigation convenience, not authorization.
- No automated deep-link smoke tests exist for any surface.

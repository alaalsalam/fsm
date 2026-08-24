# Permission-sensitive data scope matrix

This matrix covers user-facing lists/aggregations plus all remaining production `get_all` calls. There is no direct SQL or Query Builder expression in FSM application code at this revision.

| Data/read path | Query form | Scope applied before/inside query | Fields/output control | Leakage decision |
|---|---|---|---|---|
| Dispatch list and dashboard | `get_list(Service Job)` | permission query hook maps Manager→company, Technician→assignment, Customer→ownership | explicit fields; bounded list; KPI derived only from visible rows | Closed |
| Portal Jobs/Appointments | `get_list` | current Customer filter plus DocType query hook | explicit portal projections | Closed |
| Messages/feedback/returns/notes | `get_list` | root Job authorized; child query hook uses visible Job existence | explicit child fields | Closed |
| Customer profile/history | `get_list(Service Job)` | `require_customer_access` first, then visible Job query | required profile/history fields only | Closed |
| Scheduling candidates | `get_list(Technician)` | authorized Job company or resolved manager company | explicit scoring fields | Closed |
| Scheduling skill rows | `get_all(Technician Skill)` | parent Technician came from company-scoped candidate set | `skill, proficiency` only | Closed; root-scoped child read |
| Scheduling conflict rows | `get_list(Service Job)` | candidate belongs to authorized company; Job permission hooks also apply | schedule window only | Closed |
| GPS proximity | `get_list(Technician)` | Manager root Job scope and exact Job company filter | name/status/last fix only | Closed; location remains medium sensitivity |
| Cost timers | `get_all(Service Time Log)` | called only with previously authorized Job; filter is exact `service_job` | `hours` only | Closed; root-scoped child read |
| Cost estimate | `get_list(Service Job)` | resolved manager company filter | `actual_hours` only, max 1000 | Closed |
| Warehouse/Bin stock | `get_all(Bin)` | warehouses resolved from own van or manager-authorized company | quantity fields only | Closed; ERPNext child table requires explicit scoping |
| Item names/reorder levels | `get_all(Item/Item Reorder)` | item codes and warehouses come from already scoped Bin result | required name/reorder fields only | Closed; no N+1 query |
| FSM warehouse discovery | `get_all(Technician)` | manager companies or current Technician scope | warehouse only | Closed |
| Logistics Material Request/Delivery Note | `get_list` | root Job authorized, native link equals exact Job | timeline fields only | Closed |
| Return lists | `get_list(Service Return)` | child permission query condition joins visible Job | required summary fields | Closed |
| Analytics Job reads | `get_list(Service Job)` | Manager role and resolved exact company | bounded date window and explicit fields | Closed |
| Analytics Job items | `get_all(Service Job Item)` | parent IDs first obtained from company-scoped Jobs | item/qty/amount only | Closed; root-scoped child aggregation |
| Contractor reads | `get_list` | Manager role, resolved company, scoped technician/job IDs | explicit performance fields | Closed |
| Integration Job list/status | `get_list`/`db.get_value` | Manager/System Manager plus company/root Job guard | fixed integration projection and bounded limit | Closed |
| User Permission resolution | `get_all(User Permission)` | exact session user and `allow` type | `for_value` only | Closed; security metadata self-read |
| Hourly SLA scheduler | `get_all(Service Job)` | system-only scheduler intentionally global | names only | Approved system read |
| Daily manager recipient resolution | `get_all(Has Role)` | system-only scheduler; fixed FSM Manager role then enabled check | user IDs only | Approved system read |

`get_all` is retained only for child tables/system metadata where Frappe User Permissions do not supply a useful root check, and every retained user-reachable occurrence is constrained by authorized root IDs or warehouses.

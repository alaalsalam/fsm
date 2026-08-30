# Permission-sensitive data scope matrix

Date: 2026-08-26 (Phase 15 HARDENING refresh). This matrix covers user-facing lists/aggregations plus
all remaining production `get_all` calls. Since the previous revision, FSM application code **does**
contain raw SQL: five runtime `frappe.db.sql` sites (`fsm/contracts/commands.py:168,170`,
`fsm/installed_base/access.py:72,87`, `fsm/maintenance/engine.py:133`) — all parametrized `%s`
row-locks/assignment probes with server-side inputs — plus one static-fragment migration patch
(`fsm/patches/v1_0/migrate_service_request_data.py`). No user input reaches SQL text, `fields`, or
`order_by` anywhere.

| Data/read path | Query form | Scope applied before/inside query | Fields/output control | Leakage decision |
|---|---|---|---|---|
| Dispatch list and dashboard | `get_list(Service Job)` | permission query hook maps Manager→company, Technician→assignment, Customer→ownership | explicit fields; bounded list; KPI derived only from visible rows | Closed |
| Portal Requests/Jobs | `get_list` | current Customer filter plus Request/Job query hooks | explicit portal projections | Closed |
| Console Request list/detail | `get_list(Service Request/Service Job)` | Manager company/territory query hooks; Customer path requires ownership | bounded explicit fields | Closed |
| Job Visit list/detail | `get_list/get_doc(Service Visit)` | parent Job read/write authorization plus exact technician assignment for execution | explicit Visit projection | Closed |
| Service timeline | `get_list(Service Event Log)` | Request/Job/Visit root authorized before correlation filter | fixed audit fields; max 500 | Closed |
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
| Customer Site list/detail | `get_list` plus authorized-root child reads | System Manager global; Manager company/territory; Customer ownership; Technician via assigned Job Equipment | explicit site projection; max 200 | Closed |
| Installed Equipment list/detail | `get_list/get_doc` | System Manager global; Manager company; Customer ownership; Technician via assigned Job Equipment | explicit safe projection; max 200 | Closed |
| Equipment Location | `get_list` | exact Customer Site is authorized first; query hook inherits Site scope | explicit hierarchy fields; max 500 | Closed |
| Equipment History | `get_list(Service Event Log)` | Installed Equipment root is authorized first; Job IDs come from the exact equipment child links | fixed audit fields; max 1000 | Closed |
| Job Equipment | `get_all` child read | exact parent Job is authorized first | fixed equipment snapshot fields; max 500 | Closed; root-scoped child read |
| Delivery bundle entries | `get_all(Serial and Batch Entry)` | system hook operates on submitted ERPNext Delivery Note row; retry command authorizes Delivery Note company first | serial/batch/qty only | Closed; exact ERPNext bundle root |

`get_all` is retained only for child tables/system metadata where Frappe User Permissions do not supply a useful root check, and every retained user-reachable occurrence is constrained by authorized root IDs or warehouses.

CORE adds no unscoped `get_all`. Request→Job and Job→Visit reads remain permission-aware `get_list` calls. The sole Visit projection write targets its already-authorized parent Job; no Visit→Request mutation exists.

FLOW-GATE adds no guest endpoint. Operations/Visits/Exceptions/Customer 360 are Manager/System-Manager company projections. After-Sales requires both Delivery Note read permission and company scope. Contract→PM is rooted in an authorized contract and creates only same-customer/company/site equipment rows through the existing validated Maintenance command.

The commercial after-sales delta adds no Guest API. `search_submitted_delivery_notes` requires FSM Manager/System Manager and applies native read permission plus allowed-company filtering. `retry_contract_from_delivery` requires the exact Delivery Note company scope and rejects drafts/returns. Invoice/Delivery submission handlers are internal system operations rooted in a submitted ERPNext document; their `ignore_permissions` insert is not user-callable and the resulting Contract controller revalidates Customer, Company, source references, equipment, and site ownership.

## Phase 15 HARDENING delta (2026-08-26)

| Data/read path | Query form | Scope applied before/inside query | Fields/output control | Leakage decision |
|---|---|---|---|---|
| Portal hub (`fsm/portal.py:16`) | `get_list` ×6 + `get_all` native docs + `db.count` | server-resolved current Customer on every filter; Quotation/Sales Invoice keyed to owned Job names | fixed customer-safe projections; bounded limits | Closed |
| Report/Certificate detail (`fsm/reporting.py:178,183`) + REST read | `get_doc` after parent-Job read guard | Job root authorized; FSM Customer passes read on own Job | **full `snapshot` returned incl. internal `labor_cost`/`materials_cost`/`total_cost`, Stock Entry values, workshop notes** | **Open — M-1 (Medium)**: owning customer sees internal costs, contradicting the portal-hub exclusion policy |
| Realtime events (`fsm/realtime.py:12,29`) | `publish_realtime` on doc update | **none** — no room/user scoping | Job summary incl. `customer_name`; Technician live GPS | **Open — H-1 (High)**: broadcast to all authenticated sessions cross-company |
| Master reads for FSM Technician role (`/api/resource`) | framework `get_list` | role read only; **no query hook** on Technician, Service Team, Subcontractor, Service Territory, Checklist Template | full role-readable fields incl. Technician phone + last GPS, Subcontractor `hourly_rate`/contact | **Open — M-2 (Medium)**: cross-company staff/partner data |
| Bin stock, technician path (`fsm/inventory.py:39-45`) | `get_all(Bin)` | own-van resolution; manager-only company check on supplied warehouse | quantity fields only | **Open — M-3 (Medium)**: technician without a van warehouse keeps an unchecked caller-supplied warehouse |
| Offline receipts (`fsm/offline.py`) | `db.get_value` + `get_doc` | receipt `user == session.user`; Mobile Command Receipt REST read is System-Manager-only | fixed result projection | Closed (failure path echoes raw `str(exc)` — L-6, Low) |
| Equipment history/QR (`fsm/installed_base/api.py:151-210`) | `get_value` token→name, then guarded reads | `require_equipment_access` before any field; Event Log hook + authorized roots | fixed audit fields; bounded | Closed (token-existence oracle only) |
| Subcontractor probe (`fsm/contractors.py:28`) | `db.get_value` before guard | company value used only for the subsequent `require_company_scope` | company name never returned | Closed for data; L-1 records the pre-guard probe/missing role gate |
| Maintenance summary (`fsm/maintenance/api.py:95`) | `db.count` (hook-bypassing) | manual current-Customer / allowed-company filters | counts only | Closed; manual filters are the sole protection |
| Contract lists (`fsm/contracts/api.py:18`) | `get_list` (no Service Contract query hook exists) | manual current-Customer / allowed-company filters | explicit fields; bounded | Closed; manual filters are the sole protection |

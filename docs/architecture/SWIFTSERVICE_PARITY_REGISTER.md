# ARCH-005 SwiftService Parity Register

Reference SHA: `520d933e755cea36a450a7fc6ab9686d9b74f3fb`. This is a capability review only. No SwiftService code or schema is included.

SwiftService contains 79 DocTypes (21 standalone and 58 child tables), 113 whitelisted methods in one large API module, zero test files, a generic resource-driven console, and ten materially implemented controllers. Classification reflects evidence in that repository, not README claims.

| Capability                        | Reference classification | Target decision                                                                                                                               | Target owner             |
| --------------------------------- | ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| Service request/complaint intake  | Implemented              | Clean-room capability in the single Service Request intake record; convert once to Service Job                                                | FSM Intake               |
| Request validation, priority, SLA | Implemented              | Candidate for clean-room implementation; policy produces Job SLA targets                                                                      | FSM Intake/Operations    |
| Installed product/base            | Partial                  | **Duplicate of ERPNext**; use Serial No/Asset plus Job Equipment links                                                                        | ERPNext Stock/Assets     |
| Warranty/AMC eligibility          | Partial                  | Candidate for clean-room entitlement evaluator over ERPNext records; do not copy Installed Base                                               | FSM Policy + ERPNext     |
| AMC Contract                      | Schema/UI only           | Evaluate ERPNext-native overlap; if gap remains, propose plan terms only after ADR approval                                                   | FSM Maintenance          |
| Engineer profile                  | Schema/UI only           | Not suitable as a separate identity; extend current Technician linked to User/Employee                                                        | FSM Workforce            |
| Engineer assignment aggregate     | Implemented              | Merge assignment into Job/Visit relation; no duplicate work aggregate                                                                         | FSM Dispatch             |
| Multi-engineer assignment         | Partial                  | Candidate for Visit Assignment child relation                                                                                                 | FSM Workforce            |
| Dispatch board                    | Partial                  | Merge useful filters/crew concepts into existing Console dispatch screen                                                                      | FSM Dispatch             |
| Visit planning and follow-ups     | Implemented              | Candidate for clean-room Service Visit supporting record                                                                                      | FSM Work Execution       |
| Customer visit confirmation       | Partial                  | Candidate command/event on Visit and Portal                                                                                                   | FSM Work Execution       |
| GPS check-in/check-out            | Implemented              | Candidate for clean-room Visit evidence with accuracy/radius policy                                                                           | FSM Work Execution       |
| Customer pin/geocoding            | Implemented              | Candidate adapter; Address remains Frappe-owned, provider configurable                                                                        | Platform Maps            |
| Live technician tracking/ETA      | Implemented              | Candidate for clean-room event/projection with privacy/retention controls                                                                     | FSM Workforce            |
| Diagnosis/failure analysis        | Implemented              | Merge as Visit/Job execution data; no competing operational aggregate                                                                         | FSM Work Execution       |
| Photos/videos/readings            | Schema/UI only           | Candidate evidence child records/attachments under Visit; apply storage policy                                                                | FSM Work Execution       |
| Sequential checklists             | Partial                  | Already implemented in KodLyft; evolve to equipment/visit scope                                                                               | FSM Work Execution       |
| Technician time/labour log        | Partial                  | Already implemented in KodLyft; harden immutability and Visit linkage                                                                         | FSM Work Execution       |
| Spare request workflow            | Implemented              | **Duplicate of ERPNext Material Request**; retain FSM command/projection only                                                                 | ERPNext Stock            |
| Van inventory                     | Schema/UI only           | **Duplicate of ERPNext Warehouse/Bin**; keep van Warehouse link and stock projection                                                          | ERPNext Stock            |
| Parts issue/return/consume        | Implemented              | **Clean-room implemented:** ERPNext Pick List/Stock Entry own reservation and posting; FSM records guarded intent/outcome and cost projection | ERPNext Stock + FSM      |
| Purchase when unavailable         | Documentation only       | ERPNext Material Request/Purchase Order/Purchase Receipt; no FSM duplicate                                                                    | ERPNext Buying/Stock     |
| Workshop/depot repair order       | Implemented              | Not suitable as a second work order; model Job type plus Visits/tasks/outcomes                                                                | FSM Operations           |
| RMA case                          | Schema/UI only           | Candidate Job subprocess/outcome; use ERPNext stock/delivery documents                                                                        | FSM Returns + ERPNext    |
| Replacement approval              | Schema/UI only           | Candidate guarded Job outcome; serial and delivery updates remain ERPNext-owned                                                               | FSM Operations + ERPNext |
| Calibration certificate           | Schema/UI only           | Candidate immutable output attached to Job/equipment after regulatory analysis                                                                | FSM Quality              |
| Preventive maintenance visit      | Schema/UI only           | Candidate generated Visit/Job occurrence under ADR-007                                                                                        | FSM Maintenance          |
| Maintenance schedule loop         | Documentation only       | Candidate clean-room plan/occurrence engine; never copy diagrams as implementation                                                            | FSM Maintenance          |
| Service report/signature          | Implemented              | Candidate immutable report projection from Job/Visits; avoid new operational owner                                                            | FSM Work Execution       |
| Estimate                          | Partial                  | **Duplicate of ERPNext Quotation**                                                                                                            | ERPNext Selling          |
| Service billing                   | Implemented              | **Duplicate of ERPNext Sales Invoice**; reject FSM billing state machine                                                                      | ERPNext Accounts         |
| Payment recording                 | Implemented              | **Duplicate of ERPNext Payment Entry**; reject FSM payment child table                                                                        | ERPNext Accounts         |
| Tax/discount/charge rows          | Schema/UI only           | **Duplicate of ERPNext pricing/tax rows**                                                                                                     | ERPNext Accounts/Selling |
| Credit note                       | Partial                  | ERPNext Sales Invoice return/credit note only                                                                                                 | ERPNext Accounts         |
| Service closure aggregate         | Implemented              | Not suitable; closure is a guarded Service Job transition                                                                                     | FSM Operations           |
| Customer feedback/NPS             | Implemented              | Already present as Service Feedback; consolidate into one model                                                                               | FSM Customer Experience  |
| Knowledge base                    | Schema/UI only           | Candidate only after checking Frappe Help/Knowledge capabilities; not phase-critical                                                          | Platform Knowledge       |
| Dashboard KPIs                    | Partial                  | Merge validated metrics into existing Analytics; revenue sourced from ERPNext                                                                 | FSM Analytics            |
| Reports                           | Partial                  | Candidate clean-room reports with defined metric owners; reference has no tests                                                               | FSM Analytics            |
| Data import                       | Implemented via UI       | Duplicate of Frappe Data Import; link to native capability                                                                                    | Frappe Platform          |
| Settings                          | Partial                  | Merge only FSM operational policies; ERP defaults remain ERPNext settings/links                                                               | FSM Configuration        |
| Responsive engineer UI            | Partial                  | Useful interaction reference only; not a native/offline mobile architecture                                                                   | FSM Mobile               |
| Offline mobile                    | Documentation only       | Candidate clean-room implementation under ADR-009; reference is not acceptable foundation                                                     | FSM Mobile               |
| Customer portal                   | Documentation only       | Keep KodLyft Portal; do not add SwiftService console routes to Portal                                                                         | FSM Customer Experience  |
| RTL/localization                  | Not suitable             | Reference is English-first; implement independently under ADR-010                                                                             | Shared Design System     |
| Generic resource CRUD screens     | Implemented              | Not suitable as target architecture; use task-specific screens and shared contracts                                                           | Shared UX                |

## Global rejection reasons

- GPL-3.0 reference code cannot be copied into the MIT KodLyft base.
- The reference duplicates ERPNext commercial and stock concepts.
- Its 113-method monolithic API and widespread permission bypass/explicit commits are not an authorization model to inherit.
- Zero tests means implemented controller depth is not evidence of production correctness.
- Many child tables reproduce timelines, attachments, taxes, payments, and state history rather than using platform primitives/events.
## Phase 8 workshop disposition

| Reference capability | Implementation status | Target decision |
|---|---|---|
| Pickup and workshop intake | Candidate clean-room → Implemented | Canonical Service Return command lifecycle |
| Repair approval, testing and QA | Candidate clean-room → Implemented | Evidence-gated Service Return states |
| Repair order | Duplicate / not suitable | Rejected; Service Job is the sole work order |
| Estimate, invoice and parts stock | Duplicate of ERPNext | Native Quotation, Sales Invoice and Stock Entry only |

No SwiftService source code was copied.

## Phase 9 reporting disposition

Service/inspection/PM reports and refill/hydro certificates were implemented clean-room as versioned approved FSM
snapshots. Any invoicing, payment or stock facts remain references to ERPNext and were classified as duplicates,
not reimplemented. No SwiftService source code was copied.

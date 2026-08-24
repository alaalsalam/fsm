# IB gate final report

Date: 2026-08-24

Branch: `develop`

Approved pre-IB HEAD: `827c45681d54056e8e4d9dec398defcdd03640e9`

Verified implementation HEAD: `9a000f4` (the gate-report commit is its immediate descendant)

## Decision

**IB-GATE: PASS.** Customer Sites, Equipment Locations, Installed Equipment, ERPNext Delivery Note provisioning, warranty/QR identity, Service Request/Job integration, authorization, and the three clients satisfy the IB-001–IB-012 acceptance gate. No subsequent feature phase is authorized by this decision.

## Delivered surface

| Measure | Result |
|---|---|
| FSM module DocTypes | 24 total; 4 added |
| DocTypes added | Customer Site, Equipment Location, Installed Equipment, Service Job Equipment |
| ERPNext custom fields maintained | 10 total; 8 added in IB and 2 pre-existing Service Job links retained |
| Whitelisted APIs | 19 added; 0 removed; authorization matrix 104/104 |
| Generic CRUD endpoints | None added |
| SwiftService source copied | No |

The IB fields added to ERPNext are six Item fields (`fsm_after_sales_section`, `fsm_serviceable`, `fsm_create_installed_equipment`, `fsm_tracking_mode`, `fsm_activation_on_delivery`, `fsm_default_warranty_days`) and two Delivery Note fields (`fsm_provisioning_status`, `fsm_installed_equipment_count`). The existing `fsm_service_job` links on Delivery Note and Material Request remain managed idempotently.

## Acceptance evidence

| Gate | Result |
|---|---|
| Customer Site / Equipment Location / Installed Equipment | PASS |
| ERPNext Customer, Item, Serial No remain sole masters | PASS |
| Delivery Note provisioning | PASS for serviceable Serial, Unit, and Quantity tracking; non-serviceable rows ignored |
| Idempotency | PASS; ten Unit-mode retries retained exactly three records; serialized retry retained exactly two |
| Serial validation / duplicate prevention | PASS, including ERPNext v16 Serial and Batch Bundle |
| Cancellation / Sales Return | PASS; equipment and history retained; state/event reconciliation applied |
| Warranty baseline | PASS; Item default days and explicit dates validated |
| QR / asset lookup | PASS; generated identity, scoped lookup, Guest denied |
| Request optional equipment link | PASS |
| Job N-equipment | PASS; duplicate and cross-customer links rejected |
| Customer / Technician / Company isolation | PASS |
| Full backend | 40/40 PASS (26 CORE regression + 14 IB) |
| Frontend unit tests | 10/10 PASS |
| Typecheck / ESLint / Prettier | PASS / PASS / PASS |
| E2E | 18/18 PASS at 390px and 1440px |
| Console / Portal / Mobile web builds | PASS / PASS / PASS |
| Fresh install + migrate | PASS on disposable site; 24 FSM module DocTypes |
| Disposable environment cleanup | PASS; exact test database/users removed and site directory sent to system Trash after evidence capture |
| Development migrate #1 / #2 | PASS / PASS; second run stable |
| Repository status | Clean after the gate commit |
| Production | Untouched |

The real ERPNext integration test created serialized stock, submitted a Delivery Note using ERPNext v16 bundle tracking, provisioned two Installed Equipment records, retried without duplication, linked the service core, and verified retained equipment history.

## Android artifact

Path: `frontend/mobile/android/app/build/outputs/apk/debug/app-debug.apk` (generated, not committed)

Size: 8,580,790 bytes

SHA-256: `e1ff4cf1846ac4dfb4f156a7d0ec50ae602b37558e53573ed60a5acf5ead6e33`

Build result: PASS using temporary `JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64` and Android SDK environment. The server's default Java configuration was not changed.

## Atomic commits

1. `a9df2be feat(equipment): add ERPNext-backed installed base`
2. `380b7e8 feat(console): add installed-base workbenches`
3. `34de0e4 test(backend): cover installed-base integration`
4. `9a000f4 docs(backend): document installed-base architecture`
5. Gate closeout documentation commit (this report)

## Residual risks and boundaries

- The Mobile production build reports a non-fatal 1.085 MB main-chunk size warning; code splitting is a later performance concern.
- Browser QR scanning depends on `BarcodeDetector`; manual equipment/asset ID entry is the supported fallback.
- Quantity tracking deliberately represents a delivery-row aggregate rather than inventing serial identities; return reconciliation therefore acts on that aggregate record.
- Equipment events reuse the append-only Service Event Log with an explicit equipment correlation, avoiding a duplicate log DocType.
- Teams, AMC, Service Contracts, preventive maintenance, inspection, refill, hydro test, workshop, replacement, advanced certificates, full offline, and full RTL redesign remain out of scope and were not started.

Production `/home/erpnext/frappe-bench-startd-prod` and all production sites were untouched.

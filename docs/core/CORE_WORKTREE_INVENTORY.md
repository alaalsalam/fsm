# CORE Worktree Inventory

Captured before CORE-CLOSEOUT corrective edits on 2026-08-24.

- Branch: `develop`
- Approved pre-CORE HEAD: `536470e5f7596e2825804fa66f7a3fde9836631c`
- Initial state: 31 tracked paths changed (including five deleted Appointment paths) and nine untracked path groups.
- Initial tracked diff: 500 insertions, 465 deletions across 32 reported files.

## Path classification

| Path | Initial state | Classification |
|---|---:|---|
| `frontend/console/src/layouts/AppShell.vue` | M | frontend adaptation |
| `frontend/console/src/lib/fsm.ts` | M | frontend adaptation |
| `frontend/console/src/router/index.ts` | M | frontend adaptation |
| `frontend/console/src/views/DispatchBoardView.vue` | M | frontend adaptation |
| `frontend/console/src/views/IntegrationsView.vue` | M | frontend adaptation |
| `frontend/console/src/views/JobDetailView.vue` | M | frontend adaptation |
| `frontend/console/src/views/JobsView.vue` | M | frontend adaptation |
| `frontend/console/src/views/RequestDetailView.vue` | new | frontend adaptation |
| `frontend/console/src/views/RequestsView.vue` | new | frontend adaptation |
| `frontend/e2e/surfaces.spec.ts` | M | frontend adaptation / tests |
| `frontend/mobile/src/lib/fsm.ts` | M | frontend adaptation |
| `frontend/mobile/src/views/JobDetailView.vue` | M | frontend adaptation |
| `frontend/mobile/src/views/JobListView.vue` | M | frontend adaptation |
| `frontend/portal/src/lib/api.ts` | M | frontend adaptation |
| `frontend/portal/src/views/AccountView.vue` | M | frontend adaptation |
| `frontend/portal/src/views/BookingView.vue` | M | frontend adaptation |
| `frontend/portal/src/views/TrackView.vue` | M | frontend adaptation |
| `frontend/ui/src/types.ts` | M | frontend adaptation |
| `fsm/analytics.py` | M | CORE required |
| `fsm/api.py` | M | CORE required / security |
| `fsm/field_service_management/doctype/service_appointment/__init__.py` | D | migration |
| `fsm/field_service_management/doctype/service_appointment/service_appointment.js` | D | migration |
| `fsm/field_service_management/doctype/service_appointment/service_appointment.json` | D | migration |
| `fsm/field_service_management/doctype/service_appointment/service_appointment.py` | D | migration |
| `fsm/field_service_management/doctype/service_appointment/test_service_appointment.py` | D | migration / backend tests |
| `fsm/field_service_management/doctype/service_event_log/` | new | CORE required / security |
| `fsm/field_service_management/doctype/service_job/service_job.json` | M | CORE required |
| `fsm/field_service_management/doctype/service_job/service_job.py` | M | CORE required |
| `fsm/field_service_management/doctype/service_request/` | new | CORE required / migration |
| `fsm/field_service_management/doctype/service_territory/service_territory.json` | M | migration |
| `fsm/field_service_management/doctype/service_visit/` | new | CORE required |
| `fsm/hooks.py` | M | security |
| `fsm/patches.txt` | M | migration |
| `fsm/patches/v1_0/` | new | migration |
| `fsm/scheduling.py` | M | CORE required |
| `fsm/security/permissions.py` | M | security |
| `fsm/security/policy.py` | M | security |
| `fsm/service_operations/` | new | CORE required / security |
| `fsm/tests/test_security.py` | M | backend tests / security |
| `fsm/tests/test_service_operations.py` | new | backend tests |
| `docs/core/CORE_WORKTREE_INVENTORY.md` | new | documentation |

No initial path was classified as accidental or unrelated. Built SPA assets changed later by verification are generated artifacts already tracked by the repository build policy; they must correspond to final source or be excluded from CORE commits if the existing policy excludes them. Android APK and Playwright outputs remain ignored and must not be committed.

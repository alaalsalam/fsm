# Phase 1 — Service Teams & Dispatch — Gate Report

**Date:** 2026-08-25
**Branch:** `develop`
**Pre-phase HEAD:** `b79b8c7` (PRE-FEATURE-GATE PASS)

---

## Objective

Support maintenance **teams**, not just a lone technician: team masters, capabilities
(skills + certifications), team-aware dispatch scoring/assignment, and team fields on
Service Job / Service Visit — reusing ERPNext + existing FSM masters, no duplication.

## Reuse decisions (write-the-minimum ladder)

| Concept | Decision |
|---|---|
| Technician | **Reused** — links to User; already carries `skills`, `territory`, `company`, `status`, `active`, van `warehouse`. Not duplicated. |
| Technician Skill | **Reused** — existing child table drives skill scoring for teams too. |
| Service Territory | **Reused** — team `territory` + ancestor matching. |
| Roles | **Reused** — `FSM Manager` (dispatcher persona), `FSM Technician`, `System Manager`. No new role created (YAGNI). |
| ERPNext Warehouse | **Reused** — team `default_warehouse` links to it; no parallel inventory. |

## Delivered surface

### New DocTypes (3)
| DocType | Kind | Purpose |
|---|---|---|
| `Service Team` | Normal | Team master: name, company, territory, team_leader, status, default_warehouse, vehicle, capacity, effective window, members table, notes. `autoname: field:team_name`. |
| `Service Team Member` | Child (`istable`) | technician, role_in_team (Team Leader/Technician/Worker/Helper/Specialist), effective window, active. |
| `Technician Certification` | Child (`istable`) | certification, authority, issued_on, expires_on — added to Technician. |

### Field additions
- **Technician**: `certifications` (Table → Technician Certification).
- **Service Job**: `assigned_service_team` (Link), `team_leader` (Link, read-only, `fetch_from: assigned_service_team.team_leader`) — in the Schedule & Assignment section.
- **Service Visit**: `service_team` (Link) — in the Execution section.

### Controller validation — `service_team.py`
- Effective window sanity (team + per-member).
- No duplicate technician on a team.
- Member company must equal team company (batched lookup — no N+1).
- Team leader must be an **active** member.
- **Overlapping-membership policy**: a technician cannot be an active member of two teams during overlapping windows.

### Dispatch engine — `scheduling.py` (extends, does not replace)
- `suggest_teams(job, limit)` — ranks teams (mirror of `suggest_technicians`), access-guarded `manager_only`.
- `assign_team(job, team)` — company + active + capacity checked; leader fetched onto the job; mirrors `assign_technician`'s safe save (status/phase unchanged, so no lifecycle-guard trip).
- `score_team(team, job, territories)` — skill (aggregated across active members + best proficiency), territory, active status, spare capacity; penalises member booking conflicts; hard-excludes over-capacity or all-members-conflicting teams.
- Helpers: `_eligible_teams`, `_team_active_members`, `_team_open_job_count` (batched, paginated-safe).

### API — `api.py`
- `get_dispatch_jobs` gains an optional `team` filter and returns `assigned_service_team` + `team_leader`.

### Permissions
- New parent `Service Team` carries the standard triplet (System Manager / FSM Manager full; FSM Technician read). Child tables inherit parent perms.
- `assign_team` / `suggest_teams` start with `require_job_access(..., manager_only=True)` — technicians and customers are blocked from dispatch actions.

## Tests written — `fsm/tests/test_service_teams.py`

18 test methods across 3 classes (all byte-compile clean):

- **TestServiceTeamModel** (8): creation/membership, duplicate member, company mismatch, leader-must-be-active-member, inactive-member-leader, member effective window, overlapping-membership rejected, non-overlapping allowed.
- **TestServiceTeamDispatch** (6): skill-first ranking, assign sets leader via fetch, cross-company assign blocked, capacity blocks assignment, suspended team behaviour, `get_dispatch_jobs` team filter.
- **TestServiceTeamAuthorization** (3, extends `SecurityFixture`): technician cannot assign, manager can assign in-company, manager cannot assign cross-company.

## Verification performed (what I could run without migrate)

| Check | Result |
|---|---|
| All 6 DocType JSON files parse | ✅ `node JSON.parse` OK |
| All new/modified Python byte-compiles | ✅ `py_compile` OK |
| Test module byte-compiles | ✅ OK |
| AST parse of engine/api/controller | ✅ OK |

## Gate status — **TEAMS-GATE: PASS (cycle 3, isolated production-clone evidence)**

Cycles 1 and 2 are retained below as historical evidence. Cycle 3 used the authorized isolated site
`digit16.digit-erp.com`, restored from a fresh `pro.digit-erp.com` backup, and passed the complete
backend and frontend gates. No production data or application code was modified.

### ⚠ Deployment ordering (important)
`get_dispatch_jobs` now selects `assigned_service_team` and `team_leader`. Until migrate lands, those
columns do not exist, so the console dispatch board (which calls `get_dispatch_jobs`) will error.
**Migrate must run before/with this deploy** — this is the normal FSM backend→pipeline flow.

---

## Manager gate cycle 1 — TEAMS-GATE: FAIL (2026-08-24)

The two schema migrations completed (exit 0). Certification then **failed**:

1. The proposed `--module fsm.tests` command discovered **zero tests** — it targets the `fsm.tests`
   *package*, which owns no tests directly. **Rejected as evidence; never used again below.**
2. Full discovery `run-tests --app fsm` failed before running: `test_service_teams.py:6` imported
   `get_dispatch_jobs` from `fsm.scheduling`, raising `ImportError` → `TestRunnerError`.

### Root cause
API-ownership mistake **in the test only**: `get_dispatch_jobs` is owned by `fsm.api` (where
`test_security` also imports it); only `suggest_teams` / `assign_team` live in `fsm.scheduling`.
The implementation was correct — no endpoint was misplaced or duplicated.

### Remediation (Phase 1, test-only — no schema change)
- Fixed the import: `get_dispatch_jobs` ← `fsm.api`; `suggest_teams, assign_team` ← `fsm.scheduling`.
- Removed unused `add_to_date`, `now_datetime` imports.
- Fixed a test-isolation defect surfaced once the import resolved: `TestServiceTeamAuthorization`
  reuses SecurityFixture's fixed-name technicians, so a team from one method leaked into the next and
  the overlapping-membership guard (correctly) rejected it. Added `_remove_stale_teams()` cleanup in
  `setUp`, mirroring SecurityFixture's own `_remove_stale_fixtures` pattern.

### Verification performed
| Check | Result |
|---|---|
| `py_compile` test + impl | ✅ |
| Real-context import (`bench console`) | ✅ `IMPORT_OK True True True` |
| Endpoint NOT duplicated in scheduling | ✅ `SCHEDULING_HAS suggest=True assign=True get_dispatch=False` |

### Test execution is environment-gated (not a code defect)
Running the suite on the populated dev site `digit16.trilogy-erp.com` fails in ERPNext's
`BootStrapTestData()` (`erpnext/tests/utils.py`) with `DuplicateEntryError('Price List',
'Standard Buying')` — it assumes a fresh test DB. **The existing baseline module
`fsm.tests.test_service_operations` fails identically**, confirming this is a pre-existing
environmental condition, not Phase 1 code. Certification must run on the clean test environment the
baseline uses (dedicated test site), not the live dev site.

### Required manager commands for gate cycle 2
- **Second migration:** NOT required — the remediation touched only `fsm/tests/test_service_teams.py`;
  no DocType/field/schema change since cycle-1 migrate.
- **Full test discovery (correct command):**
  `bench --site <clean-test-site> run-tests --app fsm`
  (discovers all `test_*.py`: 39 baseline + 18 team = 57). Optionally scope to the new module with
  `--module fsm.tests.test_service_teams`. **Do not use `--module fsm.tests`** (zero tests).

---

## Manager gate cycle 2 — non-destructive fallback FAILED; root cause + recovery (2026-08-24)

### Failed non-destructive fallback (recorded, do not reuse)
- `run-tests --app fsm --module fsm.tests.test_service_teams --skip-before-tests` → **still failed**.
  `--skip-before-tests` only skips the `before_tests` *hook*; it does **not** skip test-record
  dependency creation, which runs during per-test-class setup regardless.
- `--skip-test-records` is **deprecated and a no-op in Frappe v16** (`run-tests --help` lists it
  `DEPRECATED`); it produces zero valid evidence. **Neither flag is acceptable Gate evidence.**

### v16 test-runner inspection (evidence-based)
- `frappe/testing/environment.py:186` `_create_global_test_record_dependencies` + per-`IntegrationTestCase`
  setup call `make_test_records(doctype, commit=True)`.
- `frappe/tests/utils/generators.py` `get_missing_records_doctypes` walks each doctype's **link fields**
  and calls `get_modules(dep)` → `load_doctype_module(dep, module, "test_")`, importing e.g.
  `erpnext/.../customer/test_customer.py`.
- That import runs, at **module scope**, `erpnext/tests/utils.py:2988` `BootStrapTestData()` →
  `make_master_data()` → `make_price_list()` → `make_records(...)`.
- `make_records` guards with `frappe.db.exists(doctype, filters)` where `filters` **includes `currency`**,
  and `make_price_list` **hardcodes `currency: "INR"`**. digit16's `Standard Buying` Price List is
  **`SAR`** (verified: `SYS_CURRENCY=SAR`), so the guard misses, an insert is attempted, and the
  `field:price_list_name` primary key collides → `DuplicateEntryError('Price List','Standard Buying')`.

**This is an ERPNext-core test-harness defect (INR-hardcoded, non-idempotent) × a SAR site.** It fires
on *import* of `erpnext.tests.utils` and is unavoidable for any fsm test whose dependency graph reaches
an ERPNext master (Customer/Company/Item/Serial No/Warehouse…). The baseline `test_service_operations`
fails identically. **The approved baseline 39-test evidence was obtained on dedicated test sites, not
digit16** — the testing log shows `site=digit16-core-test.localhost` and `site=digit16-ib-test.localhost`.

### Is there a non-destructive, apps/fsm-only recovery on digit16? — **No.**
- `IGNORE_TEST_RECORD_DEPENDENCIES` / `EXTRA_TEST_RECORD_DEPENDENCIES` are read from the **resolved
  doctype's** test module, not an arbitrary test file, and would have to be added to *every* fsm
  doctype/test module for *every* ERPNext-linked doctype — brittle, alters baseline modules, and still
  cannot stop `erpnext.tests.utils` importing via other doctypes. Not a supported or reliable fix.
- Editing `erpnext/tests/utils.py` is **outside `apps/fsm`** (not permitted here).
- Aligning digit16's `Standard Buying`/`Standard Selling` to INR would touch **live master data** and
  merely moves the failure downstream (BootStrapTestData creates dozens of INR `_Test`/company/account
  records that collide with the populated SAR site). Unreliable and out of scope ("do not modify
  digit16 data").

### Minimum external authorization required (choose one)
1. **RECOMMENDED — run on a dedicated test database** (exactly how the baseline was certified). This
   never touches the live digit16 data or production. Requires the manager to relax "digit16-only / no
   new site" **for the test-run step only**, or to point to the existing `digit16-*-test.localhost`
   harness. Command: `bench --site digit16-teams-test.localhost run-tests --app fsm`.
2. **Authorize an ERPNext-core patch** making `BootStrapTestData.make_price_list` idempotent on
   `price_list_name` (or currency-agnostic / `ignore_if_duplicate`). Outside `apps/fsm`.
3. **Authorize a reversible digit16 master-data alignment** (set `Standard Buying`/`Standard Selling`
   currency to INR for the run, then restore). Touches live data; **not recommended** (likely
   downstream failures).

**TEAMS-GATE remains FAIL/BLOCKED** pending one of the above. Not claiming PASS. Not starting Phase 2.
No production site touched. No `ignore_permissions` on user-driven writes. No ERPNext duplication.
No digit16 data modified or deleted; no other site created, dropped, restored, or purged.

---

## Manager audit — commit `392840b` (console team UI) · 2026-08-25

**Verdict: VALID Phase 1 scope; included in gate evidence. Not Phase 2 work.**

- The PROJECT-COMPLETE Phase 1 spec explicitly requires the Dispatch surface to support
  **Assign Team / Reassign Team**. `392840b` implements exactly that: `suggestTeams`/`assignTeam`
  service functions + `TeamSuggestion` type + team fields on `JobDoc` (`lib/fsm.ts`, +19), and an
  Assign/Reassign Team panel + assigned-team/leader display in `JobDetailView.vue` (+99).
- **Additive only**: 118 insertions, 0 deletions; no schema change (→ no migrate needed), no new
  endpoints (calls the already-migrated `fsm.scheduling.suggest_teams` / `assign_team`), no
  contracts/AMC or any later-phase surface touched.
- Verification recorded at commit time: `vue-tsc --noEmit` exit 0 · pre-commit lint-staged
  (eslint --fix + prettier) via husky · `vite build` success · preview served the new bundle.
- Created while the gate was BLOCKED, on explicit user instruction; building remaining Phase 1
  scope during a blocked gate does not violate the phase order — only *certifying* the gate or
  starting Phase 2 would.

### Exact gate evidence still missing (unchanged)
1. Backend: `bench --site <authorized-isolated-test-site> run-tests --app fsm` — all **57** tests
   (39 baseline + 18 team). Environment-blocked as documented above.
2. Phase-1-relevant E2E (Playwright, `frontend/e2e`) on the same evidence pass.

Frontend typecheck/lint/build evidence for Phase 1 is on record (this audit + cycle-1/2 sections).
At the time of that audit, the single missing authorization was an isolated test site (or one of the
two documented alternatives), so TEAMS-GATE remained **FAIL/BLOCKED** pending that evidence. Cycle 3
below supplies it.

---

## Manager gate cycle 3 — TEAMS-GATE: PASS (2026-08-25)

The user authorized a direct, isolated restore from production into a new test site. This cycle
supersedes the earlier blocked state and closes Phase 1.

### Restore and isolation evidence

- Source (read-only apart from creating backup artifacts): `pro.digit-erp.com` on
  `/home/erpnext/frappe-bench-startd-prod`.
- Target: `digit16.digit-erp.com` on `/home/erpnext/frappe-bench16` with a separate database and DB
  user. The pre-existing `digit16.trilogy-erp.com` site was not changed.
- Fresh backup timestamp: `20260825_100623`; database, public files, private files and site-config
  backup were captured. SHA-256 checksums were recorded during the run.
- Database plus public/private files restored successfully; source site configuration and encryption
  key were not restored into the test site.
- Installed apps on target: Frappe 16.22.0, ERPNext 16.22.0, ksa_compliance 0.61.4, digit 0.0.1,
  fsm 0.0.1 and payments 0.0.1.
- Scheduler is disabled and outgoing mail is muted on the target. `developer_mode` and `allow_tests`
  are enabled only there.
- Repeated `migrate` runs completed with exit 0 and no pending migrations reported.
- Local HTTP smoke test against gunicorn with `Host: digit16.digit-erp.com` returned the expected
  application redirect (`301` to `/login`). The public hostname does not currently resolve in DNS;
  public TLS access therefore remains an infrastructure routing item, not an application-test failure.

### Test-site-only ERPNext harness normalization

ERPNext v16's test bootstrap assumes INR and specific test fixtures even when a restored operating
site uses SAR. On the isolated target only, the ZATCA test-field default, `_Test Company` fiscal year,
Standard Buying/Selling test currency, and global test currency were normalized so the upstream
bootstrap could run idempotently. These are test-environment changes and were never applied to the
production source.

### Defects found and remediated

- Two Service Team tests reused a technician already assigned to another active team. The production
  overlap guard correctly rejected that fixture. Each test now creates its own technician, preserving
  the intended capacity and suspended-team assertions.
- Console E2E assertions were English while a clean browser correctly defaults the Console to Arabic.
  Playwright now selects English in test setup via the existing `kl-lang` preference; application
  localization behavior is unchanged.

### Final acceptance evidence

| Check | Result |
|---|---|
| Full backend discovery: `run-tests --app fsm` | ✅ 57/57 passed |
| Frontend unit tests | ✅ 10/10 passed |
| Playwright E2E, mobile + desktop | ✅ 18/18 passed |
| TypeScript typecheck | ✅ Passed |
| ESLint | ✅ Passed |
| Console build | ✅ Passed |
| Portal build | ✅ Passed |
| Mobile web build | ✅ Passed (non-blocking large-chunk warning only) |
| Migrations | ✅ Repeated exit 0 |
| Production mutation | ✅ None; backup creation only |

**Final verdict: TEAMS-GATE PASS.** Phase 1 is certified on the restored isolated test site.

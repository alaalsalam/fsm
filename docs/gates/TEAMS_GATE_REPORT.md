# Phase 1 — Service Teams & Dispatch — Gate Report

**Date:** 2026-08-24
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

## Gate status — **TEAMS-GATE: IMPLEMENTED · PENDING PLATFORM MIGRATE + TEST**

The implementation is complete and statically valid. It **cannot be self-certified PASS** because
closing the gate requires:

1. **`bench migrate`** on `digit16.trilogy-erp.com` — to create the 3 new DocTypes and the new
   Service Job / Service Visit / Technician fields. Migration is a **platform-managed operation**
   this agent is not permitted to run (BildFast pipeline reserves it).
2. **`bench --site digit16.trilogy-erp.com run-tests --app fsm --module fsm.tests`** — to execute the
   18 new team tests plus the 39-test regression baseline against the migrated schema.

### ⚠ Deployment ordering (important)
`get_dispatch_jobs` now selects `assigned_service_team` and `team_leader`. Until migrate lands, those
columns do not exist, so the console dispatch board (which calls `get_dispatch_jobs`) will error.
**Migrate must run before/with this deploy** — this is the normal FSM backend→pipeline flow, flagged
here so the migrate is not skipped.

### Required manager / platform action
Run migrate, then the test suite. If all 57 tests (39 + 18) pass → **TEAMS-GATE: PASS**, proceed to
Phase 2 (Service Contracts / AMC). If any fail → report here and fix within Phase 1 only.

No production site touched. No `ignore_permissions` added on user-driven writes. No ERPNext duplication.

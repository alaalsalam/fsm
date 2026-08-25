# Preventive Maintenance data model

Date: 2026-08-25. Domain owner: **FSM Maintenance**. Canonical execution remains `Service Job`.

## Aggregate

| Entity | Kind | Responsibility |
|---|---|---|
| Maintenance Plan | Root | Customer/Site/Contract scope, timezone, horizon, grouping window, catch-up/DST policy, lifecycle, revision. |
| Maintenance Plan Equipment | Child | Explicit Installed Equipment membership and immutable Item/Site projection. |
| Maintenance Plan Line | Child | Service type, Days/Weeks/Months/Years cadence, first due date, equipment scope, lead/grace days, auto-release. |
| Maintenance Occurrence | Durable root ledger | One due obligation for one Plan revision, Line, Equipment and due date; release/reschedule/skip/completion evidence. |
| Service Job | Existing canonical root | Executes a grouped campaign; no maintenance-specific duplicate work order exists. |

## Invariants

- A Plan belongs to exactly one ERPNext Customer and Company and one FSM Customer Site.
- Every Plan Equipment record must belong to the Plan's Customer, Company and Site.
- Active plans require an active linked Service Contract when a Contract is selected.
- Schedule edits increment the Plan revision once and cancel open occurrences from the superseded revision.
- Occurrence identity is a unique SHA-256 of Plan + revision + Line row + Installed Equipment + due date.
- Occurrences cannot be created outside the PM engine or deleted; state changes require command flags.
- Rescheduling cancels the old occurrence and creates a linked occurrence via `rescheduled_from`.
- `due_at_utc`, IANA timezone and UTC offset preserve the local scheduling decision for audit.
- Released Jobs carry a unique deterministic `maintenance_release_key`; retries cannot create a second Job.

## Lifecycle

Plan: `Draft → Active ↔ Paused → Completed/Cancelled`. Occurrence: `Forecast → Due/Overdue → Released → Completed`; open occurrences may instead become `Skipped` or `Cancelled`.

Only the Plan command service owns Plan transitions. Only the PM engine/commands and the Service Job completion projection own Occurrence transitions.

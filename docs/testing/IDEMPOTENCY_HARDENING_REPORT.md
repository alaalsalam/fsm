# Idempotency Hardening Report — Phase 15

**Date:** 2026-08-26 · **Site:** `digit16.digit-erp.com` (isolated dev clone) · Production untouched.

## 1. Repeated-execution proofs (live runs on the dev site)

### 1.1 Maintenance Occurrence generation + PM job release — PASS
A 500-equipment PM campaign (1 customer / 1 site / 500 units due, `auto_release_job=1`) was created,
then `fsm.maintenance.tasks.run_daily_maintenance` was executed **twice** in succession:

| Run | Duration | Occurrences | Released Jobs |
|---|---|---|---|
| 1 | 4,957.6 ms | 500 | **1** |
| 2 (repeat) | 401.9 ms | 500 (unchanged) | 1 (unchanged) |

- **Zero duplicate occurrences** — identity key (plan + revision + line + equipment + due date) holds.
- **Zero duplicate jobs** — release key (`maintenance_release_key`) holds.
- **Grouping requirement met:** the campaign produced **1 Service Job carrying all 500
  Service Job Equipment rows** (not 500 jobs), exactly the Hotel-ABC scenario of the program spec.
- Second run is a near-no-op (12× faster), confirming convergence.

### 1.2 All registered schedulers, double-run — PASS
`flag_sla_breaches`, `notify_low_stock` (via daily digest), `update_contract_statuses`,
`run_daily_maintenance` each executed twice consecutively with document-count snapshots before/
between/after: **no count changed on any second run.**

### 1.3 Offline receipt processing — PASS (test-proven)
`fsm/tests/test_offline.py`:
- `test_successful_command_is_idempotent` — same `command_id` resent ⇒ cached result, receipt count 1.
- `test_stale_version_returns_conflict_without_mutation` — conflict path mutates nothing.
- **New in Phase 15:** `test_same_batch_sequence_shares_pre_batch_version` — a client's own ordered
  queue (update → transition on one report) no longer self-conflicts after the first apply;
  `test_external_edit_still_conflicts_across_batches` — a genuinely external edit still Conflicts.

### 1.4 Delivery Note provisioning — PASS (test-proven)
`fsm/tests/test_installed_base.py :: test_delivery_note_unit_provisioning_is_idempotent`, plus
`provisioning_key` unique index on Installed Equipment (verified in the index review). Cancel/return
paths preserve records (`…cancel_preserves_records`, `…sales_return_marks_equipment_returned…`).

### 1.5 Report/certificate generation — PASS (test-proven + key review)
`generation_key` unique columns on Service Report and Service Certificate (index review) with
regression coverage in `fsm/tests/test_reporting.py`; repeat generation with the same key returns the
existing document; revisions only via the explicit `revise_service_report` command (N+1 revision).

### 1.6 Entitlement consumption — PASS (test-proven)
Contract entitlement consumption is transactional and keyed; covered by
`fsm/tests/test_service_contracts.py` (no double consumption on retry).

## 2. Phase 15 changes affecting idempotency

| Change | Effect |
|---|---|
| Offline batch ordering by `created_at` (`frontend/mobile/src/lib/offline.ts`) | Sequential state-machine commands now apply in capture order — removes spurious Conflict/Failed churn that previously forced manual retries. |
| Batch-local version chain (`fsm/offline.py`) | A client's own ordered queue no longer self-conflicts; external-edit detection unchanged. |
| Synced-receipt pruning (7-day retention, client) | Bounded queue growth without touching idempotency (server receipts remain the source of truth). |

## 3. Verdict — **IDEMPOTENCY: PASS**
No duplicate jobs/occurrences, no double entitlement or stock consumption, no unintended
report/certificate revision under repeated execution. Scheduler second runs are no-ops.

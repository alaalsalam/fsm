# Phase 15 — Hardening / Security / Performance — Gate Report

**Date:** 2026-08-26 · **Branch:** `develop` · **Entry HEAD:** `ce0fb4be443b66ca893d15e0d70492d52d2ee086`
**Site:** `digit16.digit-erp.com` (isolated dev clone). Production untouched throughout.

## Decision — **HARDENING-GATE: PASS**

Hardening-only scope was preserved: no new features, no business modules, no Final UAT work, no
Android APK/AAB, no deploy.

## 1. Regression evidence (detail: `docs/testing/HARDENING_REGRESSION_REPORT.md`)

| Surface | Baseline | Result |
|---|---|---|
| Backend full suite | 141 | **143/143 PASS** (2 new offline tests) |
| Frontend unit | 13 | **17/17 PASS** (4 new offline-queue tests) |
| E2E 390/1440 incl. RTL | 28 | **28/28 PASS** (re-run after all changes) |
| typecheck / ESLint / Prettier | PASS | PASS |
| Console / Portal / Mobile Web builds | PASS | PASS |
| Migrate ×2 (dev site) | PASS/PASS | PASS/PASS, no-op 2nd run, 0 duplicate fixtures |

## 2. Security (detail: `docs/security/HARDENING_SECURITY_AUDIT.md`)

174 whitelisted endpoints audited; 38 runtime `ignore_permissions` registered (all guarded);
all raw SQL parametrized; schedulers non-whitelisted and idempotent.

**Findings: 0 critical · 1 high · 3 medium — ALL FIXED in this phase:**

| # | Fix |
|---|---|
| H-1 | Realtime dispatch telemetry (customer names, technician GPS) no longer broadcast to all sessions — scoped to System Managers + company-scoped FSM Managers + the involved technician (`fsm/realtime.py`). |
| M-1 | Internal costing + workshop staff notes removed from customer-reachable report snapshots at source (`fsm/reporting.py`). |
| M-2 | Technician/Subcontractor/Service Team reads company-scoped via new `permission_query_conditions` + `has_permission` hooks (`fsm/security/permissions.py`, `fsm/hooks.py`). |
| M-3 | `get_stock_levels`: pure technicians pinned to exactly their own van warehouse; no arbitrary-warehouse reads (`fsm/inventory.py`). |

**Unresolved critical/high: 0.** Isolation proofs (Customer A↛B, Technician/Team A↛Job B,
Manager A↛Company B, guest denial, QR authorization, reports/certificates/photos/signatures
ownership, offline allowlist+version+authorization) are mapped to concrete passing tests in the
audit's §4. 8 low findings accepted-as-documented; 4 test-coverage gaps recorded for Phase 16.

## 3. Permission isolation
Explicit Company A/B, Customer A/B, Technician A/B, Team A/B and portal-user fixtures run in the
backend suite (SecurityFixture and per-domain suites — all green in the 143). Server-side
enforcement only; no reliance on UI protection.

## 4. Scheduler & idempotency (detail: `docs/testing/IDEMPOTENCY_HARDENING_REPORT.md`) — PASS
500-unit PM campaign: run 1 → 500 occurrences + **1 grouped job (500 equipment rows)**; run 2 →
**zero new documents** (401 ms no-op). All four registered schedulers double-run without count
changes. DN provisioning, entitlements, report/certificate generation keys and offline receipts
prove no duplication. New offline batch-chain semantics keep client sequences convergent while
still detecting external edits.

## 5. ERPNext integration — PASS
The 143-suite regression includes the materials (Material Request/Pick List/Stock Entry), commercial
(Quotation/Sales Invoice/payment projection), provisioning (Delivery Note submit/cancel/return,
serials/bundles), workshop (native document ownership) and multi-company suites — all green; no
parallel stock/accounting logic added (audit-verified).

## 6. Performance (detail: `docs/testing/PERFORMANCE_HARDENING_REPORT.md`) — PASS
Realistic datasets built on the dev site (1/20, 10/500, 50/5,000, 500-due campaign, 1 job × 500
equipment). One real defect found and **fixed with measured evidence**: `get_customer_equipment`
N+1 (**201→2 queries** at 200 rows). Pagination proven: no path returns more than its cap (200/500)
against the 5,000-unit customer. Index review completed; **no new index justified by measurement**
at current scale (candidates documented). No blockers.

## 7. Mobile offline & bundle — PASS
Offline stability fixes: capture-order sync (`created_at` sort), Synced-receipt pruning (7-day),
`expected_version` on report/inspection commands, batch-local version chain on the ingress —
all covered by new tests. Remaining gaps documented as known limitations (photos have no server
sink by accepted Phase 13 scope; no logout flow; media store not pruned while it holds the only
photo copies). Bundle: vendor split applied — app chunk 1.1 MB → 9.9 kB; residual `vendor-ionic`
(1,147 kB raw / 250 kB gzip) classified **LOW** (`docs/mobile/MOBILE_BUNDLE_REVIEW.md`). No Android
release work.

## 8. Commits
Atomic by defect/domain (security-realtime, security-scoping, security-snapshot, offline, perf,
mobile-bundle, docs) — see git log between the entry HEAD and the gate-closure commit. No build
artifacts, no APK/AAB, no Graphify paths committed; pre-existing `.graphifyignore` and
`graphify-out/` preserved untracked.

## 9. Residual risks (accepted, documented)
1. Mobile photos remain device-local (no server sink) — Phase 16 candidate if UAT requires upload.
2. No mobile logout flow; local store not user-partitioned (server rejects cross-user command replay).
3. 8 low security findings + 4 test-coverage gaps (audit §5) — Phase 16 backlog.
4. `vendor-ionic` chunk above the 500 kB warning (LOW; local-disk delivery).
5. Uncovered index candidates recorded for growth beyond ~10k equipment.

**Phase 16 (Final UAT) is unlocked. It was not started.**

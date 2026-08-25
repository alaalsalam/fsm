# Hardening Regression Report — Phase 15

**Date:** 2026-08-26 · **Site:** `digit16.digit-erp.com` · **Branch:** `develop`

## 1. Backend — full FSM suite (`bench run-tests --app fsm`)

| Run | Total | Passed | Failed | Skipped | Runtime |
|---|---|---|---|---|---|
| Baseline confirmation (pre-hardening, HEAD `ce0fb4b`) | **141** | 141 | 0 | 0 | 21.8 s + 204.1 s (two categories) |
| **Final certification (post-hardening)** | **143** | **143** | **0** | 0 | 6.6 s + 102.9 s |

- +2 tests over baseline: `test_same_batch_sequence_shares_pre_batch_version`,
  `test_external_edit_still_conflicts_across_batches` (offline ingress chain).
- Slowest tests: `test_repeat_window_escalates_and_suggests_priority` (4.07 s),
  `test_non_extinguisher_and_unrelated_actor_are_blocked` (2.05 s) — both stable across runs.
- Flaky evidence: none — three full-suite executions during Phase 15 (141 OK, 141 OK, 143 OK) with
  zero intermittent failures. One deprecation warning noted (`limit_page_length` V17 warning in a
  commercial test's ERPNext codepath) — upstream, non-blocking.

## 2. Frontend — static checks, unit tests, builds

| Check | Result |
|---|---|
| `yarn typecheck` (all workspaces) | ✅ PASS (0 errors) |
| `yarn lint` (ESLint) | ✅ PASS |
| `yarn format:check` (Prettier) | ✅ PASS |
| Unit tests | ✅ **17/17** (baseline 13 + 4 new offline-queue tests): ui 2, console 4, portal 4, mobile 7 |
| Console build | ✅ PASS |
| Portal build | ✅ PASS |
| Mobile Web build | ✅ PASS (with new vendor split — see `docs/mobile/MOBILE_BUNDLE_REVIEW.md`) |

## 3. E2E — Playwright, 390 px + 1440 px, RTL included

- **28/28 PASS** (~1.6 min), re-run after all Phase 15 code changes.
- Projects: `mobile-390`, `desktop-1440`; includes both RTL switch specs
  (`portal switches English LTR to Arabic RTL without overflow`, `mobile switches …`).

## 4. Result vs. mandated baselines

| Surface | Baseline | Phase 15 | Regressed? |
|---|---|---|---|
| Backend | 141 | **143** | No — grew |
| Frontend | 13 | **17** | No — grew |
| E2E | 28 | **28** | No |

## 5. Migration stability (dev site only)

- `bench --site digit16.digit-erp.com migrate` run **twice**: exit 0 / exit 0; zero
  errors/tracebacks; timing-stripped outputs of run 1 and run 2 are **identical** (practical no-op).
- Post-migrate duplicate audit: FSM roles = 3 (exact), duplicated `fsm_*` custom fields = 0,
  no scheduler side effects observed. Production never touched.

# Performance Hardening Report — Phase 15

**Date:** 2026-08-26 · **Site:** `digit16.digit-erp.com` (isolated dev clone) · Production untouched.

## 1. Dataset provenance

Created on the dev site only, via the app's own command layer (`create_customer_site`,
`create_installed_equipment`, `create_plan`) driven from `bench console`
(`/tmp/perf_dataset.py`, `/tmp/perf_measure.py`); all records carry the `PERFH` label prefix.

| Scenario | Sites | Equipment | Build time |
|---|---|---|---|
| small | 1 | 20 | 0.3 s |
| medium | 10 | 500 | 5.3 s |
| large | 50 | 5,000 | 62.4 s |
| PM campaign | 1 | 500 due (auto-release) | plan create 3.0 s |
| large Job | 1 job × 500 equipment (produced by the campaign release) | — | — |

Total Installed Equipment created: **6,020**.

## 2. Measurements (server-side, per-call; queries via `SHOW SESSION STATUS 'Questions'`)

| Call | ms | Queries | Payload | Rows |
|---|---|---|---|---|
| `get_dispatch_jobs()` | 25.2 | 16 | 381 B | 1 |
| `get_dashboard_stats()` | 2.0 | 1 | 95 B | — |
| `get_customer_equipment(large)` default | 79.9 | **101 → 2** | 46.3 kB | 100 |
| `get_customer_equipment(large, limit=500→cap 200)` | 146.9 → 112.0 | **201 → 2** | 92.6 kB | 200 |
| `list_occurrences()` (500 due) | 16.9 | 1 | 162 kB | 500 |
| `service_performance()` | 53.1 | 31 | 202 B | — |
| `get_equipment_history(one unit)` | 13.2 | 4 | 377 B | — |
| PM scheduler over 500 due (first run) | 4,957.6 | — | — | 500 occ + 1 job |
| PM scheduler repeat (no-op) | 401.9 | — | — | 0 new |

## 3. Findings and fixes

### 3.1 FIXED — N+1 in `get_customer_equipment` (evidence-justified)
Each row called `get_equipment_warranty_status(row.name)` → one full `frappe.get_doc` per row, for a
value computable from the already-fetched `warranty_end_date`. Extracted pure
`warranty_status_for(end_date)` in `fsm/installed_base/warranty.py` and used it for list rows.
**Measured: 201 queries → 2 queries at 200 rows (112 ms).**

### 3.2 Pagination — PASS, no screen can fetch 5,000 rows
`get_customer_equipment` caps at `bounded_int(limit, 1, 200)` (measured: request 500 → 200 rows);
`get_dispatch_jobs` caps at 200; `list_occurrences` caps at 500. Against the 5,000-unit customer the
equipment list returns at most 200 rows / ~93 kB. Console/Portal/Mobile screens consume these capped
APIs; no unbounded fetch path was found.

### 3.3 Response sizes
Largest observed payload: 162 kB for 500 occurrences (within the maintenance workbench's explicit
limit). All other list payloads ≤ 93 kB. Acceptable; no truncation change required.

### 3.4 Indexes — no new index justified at this scale (measured decision)
Index inventory of the hot doctypes (SHOW INDEX, dev site):
- **Installed Equipment**: customer, customer_site, item_code, serial_no, company, qr_code,
  equipment_id, asset_tag, provisioning_key — all directive filters covered except `status`/
  `equipment_location`; with covered-prefix scans the 5,000-row customer answers in ≤112 ms.
- **Service Job**: company, territory, primary_technician, assigned_service_team, service_request,
  service_contract, request_operation_key, maintenance_release_key. `customer`/`status`/
  `scheduled_date` uncovered — dispatch list at current volumes: 25 ms.
- **Maintenance Occurrence**: due_date, identity_key, grouping_key, plan, equipment, customer,
  customer_site, company, release_on, released_job — fully covered; 500-due listing 17 ms.
- **Service Report / Certificate**: generation_key (idempotency) present; link-field lookups execute
  on `service_job` foreign key via parent filters at ms-scale.

Directive rule: *"Every new index needs measured justification."* At 6k equipment / 500 due
occurrences every measured path is ≤150 ms with ≤31 queries, so **no new index is justified by
evidence**; the uncovered columns are recorded here as the first candidates should volumes grow
(Service Job `customer`+`status`+`scheduled_date` composite; Installed Equipment `status`).

### 3.5 Noted (accepted, low)
- `get_dispatch_jobs` performs 16 queries for its enrichment at 1 row (permission-hook + fetch
  metadata overhead dominates); linear component is bounded by the 200-row cap.
- `service_performance` uses 31 queries of fixed fan-out (per-metric aggregates), independent of row
  volume.
- Mobile cache size: job list + detail caches store only capped API payloads (≤93 kB per entry);
  IndexedDB growth from the command queue is now pruned (7-day Synced retention).

## 4. Verdict — **PERFORMANCE: PASS**
One real defect (N+1) found and fixed with measured before/after evidence; pagination proven at the
5,000-row scale; PM campaign scheduler converges idempotently in ~5 s for 500 units; no
evidence-justified index additions at current scale; no blockers remain.

# IB test report

Date: 2026-08-24. Source baseline: `827c45681d54056e8e4d9dec398defcdd03640e9`, branch `develop`.

## Environments

- Fresh install: disposable `digit16-ib-test.localhost` in `/home/erpnext/frappe-bench16`; Frappe 16.22.0, ERPNext 16.22.0, FSM develop.
- Upgrade: `digit16.trilogy-erp.com` only. Two consecutive migrations completed successfully.
- Production `/home/erpnext/frappe-bench-startd-prod`: untouched.

## Results before final committed rerun

| Check | Result |
|---|---|
| Fresh install + migration | PASS; 24 FSM module DocTypes |
| Existing backend regression | PASS 26/26 |
| Installed Base focused backend | PASS 14/14 |
| Real serial stock Delivery Note | PASS; two v16 bundle Serial Nos provisioned and retry count unchanged |
| Unit retry idempotency | PASS; ten retries retained three records |
| Cancellation / Sales Return | PASS; records retained and lifecycle events emitted |
| Customer / Technician / Company isolation | PASS |
| Typecheck | PASS all six workspaces |
| ESLint / Prettier | PASS |
| Frontend unit tests | PASS 10/10 |
| Console / Portal / Mobile builds | PASS |
| E2E | PASS 18/18 across 390px and 1440px |
| Android debug | PASS with temporary Java 17 and Android SDK env |
| Development migrate #1 / #2 | PASS / PASS |

Final committed HEAD rerun and artifact hash are recorded in `docs/gates/IB_GATE_FINAL_REPORT.md`.

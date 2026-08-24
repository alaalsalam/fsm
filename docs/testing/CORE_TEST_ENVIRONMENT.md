# CORE test environment

Date: 2026-08-24. Dedicated disposable site: `digit16-core-test.localhost`; database `_digit16_core_test`. Tests were enabled and the same site was reused throughout closeout.

| App | Version/branch | Git SHA at site creation |
|---|---|---|
| frappe | 16.22.0 / version-16 | `567c05b6b7b736b52f08c372a620bd19cba168d1` |
| erpnext | 16.22.0 / version-16 | `054b20a2ae1bdea44694cca72d17412945171cab` |
| payments | 0.0.1 / develop | `86fefa9faf8ad825fe6f08c4753acfe44817900b` |
| fsm | 0.0.1 / develop | candidate working tree based on `536470e5f7596e2825804fa66f7a3fde9836631c` |

Payments is present because ERPNext test fixture setup expects Payment Gateway support; it is not an FSM runtime `required_apps` dependency.

## Results

| Check | Result | Runtime/evidence |
|---|---|---|
| targeted `fsm.tests.test_service_operations` | 13/13 PASS | 27.34s final run |
| full `bench ... run-tests --app fsm` | 26/26 PASS | 31.15s final pre-commit run |
| GATE-001 regression subset | PASS | 13 legacy backend tests remain included; total increased to 26 |

The first fixture-populating targeted run took 2m47s while ERPNext test fixtures were generated. Subsequent reused-site runs took about 27–39s. There were zero failed or skipped tests. A Frappe v17-removal warning for deprecated `limit_page_length` was emitted by framework query compatibility and did not affect v16 results.

The site/database and their temporary database users are removed only after final committed-state verification.

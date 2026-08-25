# Coverage and entitlement engine

The server-side evaluator is `fsm/contracts/coverage_engine.py`. Frontends display its decision and never
calculate coverage independently.

Decision order:

1. Active Installed Equipment warranty → `Warranty`.
2. Explicit Job contract, otherwise the most recent matching Active contract for Customer/Company/date.
3. Site/equipment/category scope match.
4. Most-specific active service/category rule.
5. Active matching visit entitlement and remaining quantity.
6. Result: `Contract Covered`, `Partially Covered`, `FOC`, `Not Covered`, or `Chargeable`.

The decision includes reason, covered labour/parts/travel, optional limits, and remaining entitlement. It
does not create an ERPNext invoice.

Consumption uses a row lock on the Contract and a unique `idempotency_key`. Retrying the same command returns
the existing consumption and never decrements the entitlement twice. Consumption evidence is append-only.

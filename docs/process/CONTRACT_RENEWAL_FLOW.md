# Contract renewal flow

`Contract → covered sites/equipment → coverage/entitlements → PM Plans → consumption → expiry projection → renewal quotation → renewed contract → PM continuity`.

Renewal copies policy rows into a new Draft contract, resets usage and preserves `renewed_from`. Entitlement consumption uses a durable idempotency key. ERPNext Quotation remains the commercial source of truth.

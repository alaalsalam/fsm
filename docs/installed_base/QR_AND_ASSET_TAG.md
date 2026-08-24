# QR and asset tag

Each Installed Equipment receives a stable `equipment_id` and QR token equal to the non-sensitive FSM identifier, for example `FSM-EQ-000001`. Customer name, address and complete Serial No are not encoded in the payload. `asset_tag` is an optional separate unique physical label.

`resolve_equipment_by_qr(token)` requires authentication and then applies the same Installed Equipment data-scope guard as direct lookup. Guest access is denied. Customer users can resolve only their equipment; technicians only equipment on assigned Jobs; Managers remain company scoped.

Console provides a QR display/print baseline. Mobile supports token entry and on-device QR image decoding through the WebView BarcodeDetector when available, with explicit asset-ID fallback. There is no public QR page in this phase.

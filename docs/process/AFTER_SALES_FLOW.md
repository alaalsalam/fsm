# After-sales flow

`Customer → Project optional → Sales Order → Delivery Note → Installed Equipment → Site/Location → Installation/Warranty → Contract optional → Maintenance Plan optional → First Due`.

Delivery Note submit remains the idempotent provisioning trigger. `After-Sales Setup` reads the submitted Delivery Note and the equipment already provisioned from it, shows missing sites/locations and installation readiness, then points to existing installed-base, contract and PM commands. It never creates duplicate equipment.

# ERPNext integration matrix

| Concept | System of record | FSM behavior |
|---|---|---|
| Customer | ERPNext Customer | Link and authorize; never copy a master |
| Address/Contact | ERPNext | Site validates Dynamic Link ownership; display fields are read-only projections |
| Product | ERPNext Item | Link and read after-sales policy/custom fields |
| Serial/Batch | ERPNext | Validate existence/item; read Delivery v16 bundle entries |
| Delivery proof | ERPNext Delivery Note | Submit hook provisions; cancellation/return project lifecycle |
| Sales Order/Invoice | ERPNext | Optional links only |
| Warehouse/stock ledger | ERPNext | No FSM stock representation |
| Customer service location | FSM Customer Site | Operational site and optional hierarchy |
| Installed product | FSM Installed Equipment | After-sales identity, lifecycle, QR, location and history correlation |
| Work scope | FSM Service Job | N equipment through Service Job Equipment |

Multi-company checks require equipment, site and Delivery Note company/customer alignment. No ERPNext source file was modified.

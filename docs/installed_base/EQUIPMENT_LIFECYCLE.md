# Equipment lifecycle

| Current | Allowed next states | Command/event |
|---|---|---|
| Pending Installation | Active, Inactive, Removed, Returned | `confirm_installation` or `change_equipment_status` |
| Active | Inactive, Removed, Returned, Replaced, Disposed | explicit status command |
| Inactive | Active, Removed, Returned, Disposed | explicit status command |
| Removed | Active, Returned, Disposed | explicit status command |
| Returned | none | terminal in this phase |
| Replaced | none | terminal in this phase |
| Disposed | none | terminal in this phase |

Direct status writes are rejected. Installation validates the Customer Site and optional Equipment Location, records installation/commissioning dates, activates the record, and emits `InstallationConfirmed` plus `EquipmentActivated`. Moves preserve customer/company ownership and emit `EquipmentMoved`. Delivery cancellation and return use the lifecycle rather than deletion.

Warranty is a projection. Start basis is configured as Delivery Date, Installation Date or Commissioning Date. The Item warranty-day policy determines the end date; the read helper recomputes Active/Expired against the current date rather than trusting the stored label.

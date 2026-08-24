# ERPNext custom field register

Fields are created idempotently by `fsm.setup.ensure_custom_fields` during install and after migrate. Uninstall cleanup is manual because deleting business configuration automatically would be destructive.

| DocType | Field | Purpose |
|---|---|---|
| Item | `fsm_after_sales_section` | section marker |
| Item | `fsm_serviceable` | eligibility for FSM service |
| Item | `fsm_create_installed_equipment` | explicit provisioning opt-in |
| Item | `fsm_tracking_mode` | Serial / Unit / Quantity / None |
| Item | `fsm_activation_on_delivery` | Active instead of Pending Installation |
| Item | `fsm_default_warranty_days` | baseline warranty duration |
| Delivery Note | `fsm_service_job` | pre-existing optional Job link |
| Delivery Note | `fsm_provisioning_status` | Completed / Cancelled / Return Reconciled projection |
| Delivery Note | `fsm_installed_equipment_count` | read-only provisioned count |
| Material Request | `fsm_service_job` | pre-existing optional Job link |

No Material/Stock field was added for Installed Base.

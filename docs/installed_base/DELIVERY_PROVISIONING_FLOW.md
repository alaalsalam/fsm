# Delivery provisioning flow

## Submit path

1. ERPNext validates and submits Delivery Note.
2. The thin `doc_events` hook calls `fsm.installed_base.provisioning.on_delivery_note_submit`.
3. Return notes enter return reconciliation; normal deliveries enter provisioning.
4. Each row is eligible only when Item has both `fsm_serviceable` and `fsm_create_installed_equipment`.
5. Tracking policy produces identities:
   - Serial: one identity per ERPNext Serial No, including v16 Serial and Batch Bundle entries.
   - Unit: one identity per whole unit sequence.
   - Quantity: one aggregate identity and quantity.
   - None: no record.
6. SHA-256 of Delivery Note + row name + identity becomes the unique `provisioning_key`.
7. The service inserts only missing Installed Equipment, emits `EquipmentProvisioned`, and optionally `EquipmentActivated`.
8. Delivery Note receives read-only provisioning status and equipment count.

The public retry command is `provision_delivery_note(delivery_note)` and requires Manager/System Manager company scope. `reconcile_delivery_note_provisioning` applies the same guard. Hook execution is a system operation reached only after ERPNext has submitted the exact document.

## Retry and concurrency

Lookup by unique provisioning key handles normal retries. The database unique constraint plus duplicate-error recovery handles concurrent retries. The acceptance test calls the retry command ten times and retains the same count.

## Cancel and return

- Cancelling the source Delivery Note never deletes equipment. Non-terminal records become `Inactive` and receive `DeliveryCancelled`.
- A Sales Return selects canonical Serial Nos from its bundle where available; otherwise it selects the required count from the returned source/item. Records become `Returned` and receive `EquipmentReturned`.
- Existing Job links and event history are retained.

## Failure semantics

Provisioning runs in the Delivery Note submit transaction. Validation failure aborts submission rather than leaving an unprovisioned eligible delivery marked successful. Reconciliation is the explicit repair route.

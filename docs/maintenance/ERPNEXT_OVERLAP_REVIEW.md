# ERPNext maintenance overlap review

Decision: **retain FSM Maintenance Plan/Occurrence and do not copy or replace ERPNext Maintenance Schedule/Visit**.

ERPNext v16 `Maintenance Schedule` is tied to Customer/Item/Sales Order scheduling and generates ERPNext `Maintenance Visit` records. It does not provide the required Installed Equipment occurrence ledger, Plan revisions, durable skip/reschedule lineage, configurable due/grace/release policies, or deterministic many-equipment grouping into the canonical FSM Service Job.

| Concept | Owner | Integration decision |
|---|---|---|
| Customer, Item, Serial No, Sales Order | ERPNext | Referenced as commercial/product truth. |
| ERPNext Maintenance Schedule/Visit | ERPNext | Not duplicated, imported, or used as a second FSM work order. Existing ERPNext records remain native. |
| Installed Equipment recurrence policy | FSM Maintenance Plan | Clean implementation against FSM Installed Base. |
| One due obligation and its history | FSM Maintenance Occurrence | Durable FSM scheduling evidence. |
| Operational execution | FSM Service Job/Visit | Sole execution aggregate; released from occurrences. |
| Stock, invoice, collection | ERPNext | Never authored by Plan or Occurrence. |

This boundary satisfies ADR-007: the occurrence engine owns scheduling obligations, while Service Job owns execution and ERPNext owns commercial/stock/accounting truth.

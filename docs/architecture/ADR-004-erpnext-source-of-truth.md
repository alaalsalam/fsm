# ADR-004: ERPNext owns commercial, stock, billing, and collection truth

- Status: Accepted
- Date: 2026-08-24

## Context

Duplicating Item, inventory, estimates, invoices, payments, or ledger states in FSM causes reconciliation and permission failures.

## Decision

ERPNext v16 owns Customer-related commercial masters, Item/Serial No/Asset, Warehouse/Bin/Stock Ledger, Quotation/Sales Order/Delivery Note, Material Request/Stock Entry, Sales Invoice, Payment Entry, taxes, GL, and outstanding balances. FSM issues authorized commands, stores native document links, and renders read-only projections.

## Consequences

- Job amounts are operational estimates, not accounting revenue.
- No Service Billing, Bill Payment, Van Inventory, Service Estimate, or spare-procurement replica is created.
- Reconciliation prefers ERPNext records and ledgers.
- ERPNext permission checks occur before any narrowly justified internal bypass.

## Approval gate

Every field labeled amount, stock, invoice, paid, delivered, or warranty must identify its authoritative ERPNext source or be explicitly labeled an operational estimate/snapshot.

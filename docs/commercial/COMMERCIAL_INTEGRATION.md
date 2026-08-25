# Commercial integration

Date: 2026-08-25. Status: implemented.

FSM classifies each Service Job Item as Covered or Billable by applying the Warranty/Contract coverage engine to
its equipment and component (service/labour, spare, consumable or refill). Guarded commands create/link native
ERPNext Quotation and Sales Invoice documents containing billable lines only. Payment status is a read projection
of the linked Sales Invoice. FSM stores no invoice, payment, tax or GL state.

Profitability is analytics only: ERPNext invoice revenue less labour, consumed material, travel, overhead and total
operational cost. It is available by Job and as company-scoped rows filterable by Customer or Contract.

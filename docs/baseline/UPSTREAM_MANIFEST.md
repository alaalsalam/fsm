# BASE-006 Upstream Manifest

## Approved source inputs

| Component | Repository | Branch | Recorded SHA | Role |
|---|---|---|---|---|
| KodLyft FSM | `https://github.com/alaalsalam/fsm.git` | `develop` | `de4dd177781dd0d7eba2aad7825f0c4b19c1fef6` | Sole application codebase |
| SwiftService | `https://github.com/alaalsalam/swiftservice.git` | `develop` | `520d933e755cea36a450a7fc6ab9686d9b74f3fb` | Functional reference only; no code copying |
| Frappe | Local v16 checkout | `version-16` | `567c05b6b7b736b52f08c372a620bd19cba168d1` | Framework engine |
| ERPNext | Local v16 checkout | `version-16` | `054b20a2ae1bdea44694cca72d17412945171cab` | Sales, stock, invoicing, and collection source of truth |
| Frappe Payments | `https://github.com/frappe/payments.git` | `develop` | `86fefa9faf8ad825fe6f08c4753acfe44817900b` | Official owner of `Payment Gateway`; ERPNext v16 test/dev dependency |

## Derived project commits

| Commit | Purpose |
|---|---|
| `67c0475f7875e8de43bf4cdb01157ccc27561daa` | Preserve the SPA `www` output directory so clean Console/Portal builds can copy their entry files |

Documentation commits are additive to this manifest and do not change the approved upstream source SHA.

## Provenance rules

- Only KodLyft FSM files may become application source.
- SwiftService may supply capability names, workflows, acceptance ideas, and risk discoveries only.
- No SwiftService source, generated asset, schema JSON, text block, or implementation is copied into FSM.
- Any accepted parity item must be independently designed against ERPNext v16 and implemented clean-room after ADR approval.
- ERPNext documents remain authoritative for Customer/Contact/Address, Item/Serial No/Asset, Warehouse/Bin, Quotation, Sales Order, Delivery Note, Material Request, Stock Entry, Sales Invoice, Payment Entry, and their ledgers.

## Reference isolation evidence

SwiftService was cloned to `/tmp/swiftservice-reference.ivm9la`, outside the bench and FSM repository. The FSM worktree contains no path or tracked file named `swiftservice`.

## Version caveats

- The local Frappe and ERPNext checkouts have no configured `origin` remote, so their recorded commit SHAs—not a remote URL—are the reproducibility anchor.
- The designated execution site is `digit16.trilogy-erp.com` in the v16 development bench. Its installed apps are `frappe`, `erpnext`, `ksa_compliance`, `crm`, `fsm`, and official `payments`. The clean GATE test site is removed after final evidence collection.
- The source manifest declares Node 20 support, while the frozen frontend dependencies require Node 22.12 or later.

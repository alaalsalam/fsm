# ARCH-002 State Ownership Matrix

Status: **Proposed**

Only the owner may author a state. Other domains consume projections or react to events; they do not copy the state into a competing authoritative field.

| Aggregate/document | Proposed states | State owner | Permitted command actors | Projection consumers |
|---|---|---|---|---|
| Service Request | New, Triaged, Accepted, Rejected, Converted, Cancelled | FSM Intake | Customer creates; Manager triages/converts | Portal, Console, Job creation |
| Service Job | Draft, Planned, Assigned, En Route, In Progress, On Hold, Completed, Cancelled | FSM Operations | Manager plans/assigns/holds/cancels; assigned crew starts/completes within guards | Console, Mobile, Portal, Analytics |
| Service Visit | Planned, Confirmed, En Route, Checked In, In Progress, Completed, Aborted, No Access | FSM Work Execution | Manager schedules; assigned crew executes | Job projection, Portal ETA, Maintenance |
| Checklist Result | Pending, In Progress, Passed, Failed, Not Applicable | FSM Work Execution | Assigned crew; manager may reopen with audit reason | Job completion guard, report projection |
| Technician duty | Off Duty, Available, Busy | FSM Workforce | Technician duty commands; Job/Visit events derive Busy | Dispatch |
| Service Return | Requested, Approved, Received, Closed, Cancelled | FSM Returns | Technician requests; Manager approves; warehouse receiver receives | Job timeline, ERPNext stock link |
| Maintenance Plan | Draft, Active, Paused, Ended, Cancelled | FSM Maintenance | Maintenance Manager | Occurrence generator |
| Maintenance Occurrence | Pending, Generated, Skipped, Superseded, Failed | FSM Maintenance engine | Scheduler plus authorized manager skip/retry | Request/Job link, audit |
| Quotation | ERPNext native lifecycle | ERPNext Selling | ERPNext-authorized sales actors | Job commercial projection |
| Material Request | ERPNext native lifecycle | ERPNext Stock | ERPNext-authorized stock/procurement actors | Job logistics projection |
| Stock Entry | ERPNext native docstatus/workflow | ERPNext Stock | ERPNext-authorized stock actors | Job consumption/return projection |
| Sales Invoice | Draft, Submitted, Cancelled plus ERPNext payment status | ERPNext Accounts | ERPNext-authorized accounts actors | Job billing projection |
| Payment Entry | Draft, Submitted, Cancelled | ERPNext Accounts | ERPNext-authorized collection actors | Invoice outstanding projection |

## Service Job transition rules

| From | To | Required guard | Event |
|---|---|---|---|
| Draft | Planned | Customer, equipment scope, service address, schedule window valid | `service_job.planned` |
| Planned | Assigned | At least one eligible technician/crew assignment | `service_job.assigned` |
| Assigned | En Route | Actor is assigned to an active Visit | `service_visit.travel_started` |
| Assigned/En Route | In Progress | Valid visit check-in or manager override with reason | `service_job.started` |
| In Progress | On Hold | Reason code and next action required | `service_job.held` |
| On Hold | In Progress | Hold resolution recorded | `service_job.resumed` |
| In Progress | Completed | Required visits/checklist/equipment outcomes and time evidence complete | `service_job.completed` |
| Draft/Planned/Assigned/On Hold | Cancelled | Authorized role, reason, ERPNext side effects reconciled | `service_job.cancelled` |

`Completed` is not equivalent to paid, invoiced, delivered, or stock-posted. Those are ERPNext projections. Reopening a completed Job requires an explicit reopen command and event; it must not silently edit historical completion.

## Current-state reconciliation

The current Service Job states map as follows: Draft→Draft, Scheduled→Planned, Assigned→Assigned, In Progress→In Progress, On Hold→On Hold, Completed→Completed, Cancelled→Cancelled. `En Route` becomes explicit only after Visit exists. The current controller derives some state from checklist rows; target transitions must be command-based and audit logged, while checklist completion remains a guard.

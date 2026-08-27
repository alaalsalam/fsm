# Next action rules

| Record | State/condition | Projection |
|---|---|---|
| Request | Open/Triaged | Triage or convert to Job |
| Request | Converted | Open linked Job |
| Job | Draft/Planned/Scheduled | Plan, schedule, assign or dispatch |
| Job | In Progress | First structured completion blocker, otherwise generate/submit report when policy requires |
| Visit | Planned/Dispatched/En Route/Checked In/In Progress | Dispatch, travel, check in, work, check out |
| Occurrence | Due/Overdue | Release grouped Job |
| Occurrence | Released | Open released Job |
| Contract | Draft/Active/expiring | Activate, view/create PM, renew |
| Service Return | non-terminal | Continue workshop lifecycle |

Next Action is a projection and never a stored status.

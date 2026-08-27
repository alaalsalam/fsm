# Completion policy

`complete_job` evaluates structured blockers before transition. Current blockers cover active visits, incomplete checklist tasks, unresolved critical failures, open workshop cases and service-type-configured inspection/report/certificate requirements.

Inspection, report and certificate requirements are configured in Service Settings as one Service Type per line. Empty settings preserve compatible flows. Each blocker includes code, localized message, action, route and responsible actor. Coverage, material and PM idempotency remain enforced by their owning domain services rather than duplicated in the policy.

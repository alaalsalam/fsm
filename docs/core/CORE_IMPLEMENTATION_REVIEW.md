# CORE implementation review

Review date: 2026-08-24. Candidate base: `536470e5f7596e2825804fa66f7a3fde9836631c` on `develop`.

## PASS decisions

- Service Request 1:N Service Job 1:N Service Visit is physical and tested; Service Job remains the canonical work order.
- Request, Job, and Visit lifecycle mutations are command/state-service owned. Controller guards reject generic status/phase writes.
- Authorization executes before every mutation; Manager company/territory, Customer ownership, and assigned Technician boundaries reuse the GATE-001 policy layer.
- Visit projections only update its parent Job phase/status. There is no Visit→Request write, circular save chain, or checklist lifecycle owner.
- Event Log creation is internal-only and rows are append-only; API create, modify, and delete paths are tested negative.
- Request-to-Job retry is sequentially and concurrently protected by a unique operation key.
- Completed/Cancelled are terminal and active Visits block Job completion.

## Defects found and corrected

1. Generic Request insert could forge a non-Draft initial state: controller initial-state guard added.
2. Request conversion retry had no database serialization point: unique SHA-256 operation key and duplicate-winner recovery added.
3. Job/Visit schedule windows accepted reversed timestamps: explicit end-after-start validation added.
4. Dispatch/create Visit accepted inactive or cross-company technicians: active/company validation added.
5. Technician Visit execution accepted a blank or different assignment, and mixed Manager/Technician roles were mis-prioritized: exact assignment enforced only for technician-only actors.
6. Visit read APIs reused write access: a separate scoped read guard was added.
7. Visit creation allowed Draft/terminal Jobs: restricted to active planned work.
8. Job cancellation was not manager-only: manager guard added.
9. User-visible Appointment wording and stale frontend naming were corrected.
10. E2E mocks intercepted workspace API source modules: interception was narrowed to actual `/api/method` and `/api/resource` requests and execution serialized for stable lazy-route compilation.

## Verification

- Targeted CORE backend: 13/13 PASS.
- Full FSM backend: 26/26 PASS; zero failures/skips.
- Existing security baseline remains included and green.
- Frontend unit tests: 10/10 PASS; typecheck, ESLint, Prettier PASS.
- E2E: 12/12 PASS at 390px and 1440px.
- Console, Portal, Mobile web, and Android debug builds PASS.
- Development migrate completed successfully on repeated runs.

## Remaining risks

- Mobile production chunk is about 1.1 MB before gzip; code splitting is a performance follow-up, not a CORE correctness failure.
- Android reports upstream SDK XML/Gradle deprecation warnings; build remains successful with AGP 8.13.0/Gradle 8.14.3.
- Event Log is transactional audit storage, not an outbox; no external-delivery guarantee is claimed.
- Terminal reopen, offline command replay, multi-technician Visit assignments, Installed Base, PM/AMC, Workshop, and RTL redesign remain out of scope.

# Frontend test report — GATE-001

- Date: 2026-08-24
- Node: 24.16.0
- Package manager: Yarn 1.22.22 workspaces
- Result: **PASS**

## Unit/component foundation

| Surface | Coverage added | Result |
|---|---|---|
| Console | App router outlet boot; anonymous protected redirect; authenticated login redirect; session API failure fails closed | 4 tests passed |
| Portal | anonymous account redirect; signed-in auth-page redirect; forbidden Job API error propagated; failed session load fails closed | 4 tests passed |
| Mobile Web | Ionic app/router outlet boot; offline fetch error surfaced | 2 tests passed |

Command: `yarn test`. Total effective GATE tests: **10 passed**. Design/UI/API workspaces retain their existing no-test behavior and exit successfully with `--passWithNoTests`.

## E2E smoke

Playwright starts isolated Vite servers for Console, Portal, and Mobile. The same smoke suite runs with viewports 390×844 and 1440×900:

- Console `/jobs` boots and redirects anonymous users to `/login`.
- Portal booking surface boots and renders `Request a service`.
- Mobile `/jobs` boots while the API origin is unavailable and renders its fallback state without an unhandled page error.

Command: `yarn test:e2e`. Result: **6/6 passed**.

## Static/build checks

| Command | Result |
|---|---|
| `yarn typecheck` | PASS across all six workspaces |
| `yarn lint` | PASS |
| `yarn format:check` | PASS after generator hardening |
| `yarn build` | PASS for Console, Portal, and Mobile |

`design/build-tokens.mjs` now formats its TypeScript output using the repository Prettier contract, so a token build no longer makes the worktree format check fail. The known Mobile main-chunk size warning remains recorded as performance debt.

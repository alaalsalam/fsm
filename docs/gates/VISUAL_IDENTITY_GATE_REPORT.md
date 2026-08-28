# Visual Identity Gate Report

**Gate:** `IDENTITY-GATE`  
**Environment:** `/home/erpnext/frappe-bench16` / `digit16.digit-erp.com`  
**Production:** out of scope and untouched

## Scope

This gate aligns Frappe Desk, Console, Portal, Mobile Web, and the existing Android shell with the canonical DIGIT identity. It does not add business features, change API contracts, deploy production, sign an APK/AAB, or create an iOS native project.

## Evidence matrix

| Check | Result |
|---|---|
| Canonical DIGIT colors in shared token source | PASS — generated CSS, Ionic, Tailwind, and TypeScript outputs rebuilt from `tokens.json` |
| IBM Plex Sans Arabic and Archivo bundled locally | PASS — four weights of each family; SaudiRiyal isolated to currency marks |
| External Google Fonts removed | PASS — no remote font tags and E2E resource assertion passed |
| Shared DIGIT wordmark component used by all web surfaces | PASS — Console, Portal, and Mobile Web use `DigitBrand` |
| Frappe app icon, Workspace, and sidebar aligned | PASS — database values verified after two migrations |
| Android launcher, adaptive icon, splash, and app name aligned | PASS — generated from official assets and verified inside the debug APK |
| Arabic/English and RTL/LTR preserved | PASS — localization regression passed without horizontal overflow |
| Console build | PASS |
| Portal build | PASS |
| Mobile Web build | PASS — existing Ionic vendor chunk warning remains non-blocking |
| Frappe v16 asset build | PASS — Node 24 bench toolchain |
| TypeScript / ESLint / Prettier | PASS / PASS / PASS |
| Frontend tests | PASS — 17/17 |
| E2E at 390px and 1440px | PASS — 30/30 |
| Android Debug build | PASS — Gradle 423 tasks, application label `DIGIT Field Service` |
| Development migrate | PASS / PASS |

## Visual review

Rendered review was completed at `1440x900` and `390x844` for the Console shell, Portal, and Mobile Web. The final pass confirmed:

- official wordmark geometry remains unmirrored in both directions;
- deep-green navigation and paper surfaces match the DIGIT product hierarchy;
- all Console domains have distinct semantic icons;
- the mobile Console navigation exposes five primary destinations without overflow;
- Arabic/English direction switching preserves layout and logo orientation;
- no clipped Latin glyphs remain after isolating the SaudiRiyal font to currency marks.

## Development database evidence

After `migrate` was run twice, the records remained stable:

| Record | Verified identity |
|---|---|
| Desktop Icon / Field Service | label `DIGIT Field Service`, icon `wrench`, official FSM asset URL |
| Workspace Sidebar / Field Service | title `DIGIT Field Service`, header icon `wrench` |
| Workspace / Field Service | label `DIGIT Field Service`, icon `wrench`, green indicator, visible |

The after-migrate updater changes identity metadata only and is idempotent; routes, roles, permissions, and workspace links are not changed.

## Compatibility boundaries

- `fsm` remains the Frappe app name.
- `@kodlyft/*` remains the internal workspace namespace.
- `com.kodlyft.fsm` remains the Android application ID to preserve upgrade compatibility.
- The current repository does not contain an iOS native directory; iOS asset generation is therefore not claimed by this gate.

## Final status

`IDENTITY-GATE: PASS`

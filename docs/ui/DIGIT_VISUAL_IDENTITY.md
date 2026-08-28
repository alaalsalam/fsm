# DIGIT Field Service Visual Identity

## Decision

FSM is presented as **DIGIT Field Service**. `fsm` remains the application and package name, and DIGIT FSM remains the functional codebase required by the architecture ADRs. The visible product identity is owned by DIGIT.

The canonical identity source is the installed development app at `/home/erpnext/frappe-bench16/apps/digit`. Identity assets and tokens are reused from that source, while the approved integration adds a conditional FSM entry to the DIGIT shell. No functional code was copied from another FSM product.

## Canonical tokens

| Role | Value |
|---|---|
| Primary brand | `#0A8754` |
| Deep brand/chrome | `#064E3B` |
| Deep operational floor | `#032D23` |
| Mint accent | `#34D399` |
| Soft brand surface | `#E6F3EC` |
| Paper background | `#F4F3EE` |
| Primary ink | `#0B1F17` |
| Body ink | `#33433B` |
| Muted ink | `#71807A` |

`frontend/design/tokens.json` is the FSM source of truth. Generated CSS, Ionic variables, Tailwind mappings, and TypeScript exports must be rebuilt with `yarn tokens`; generated files are not edited directly.

## Typography

- Arabic and interface text: IBM Plex Sans Arabic.
- Latin labels and tabular numbers: Archivo.
- Saudi currency glyph: SaudiRiyal, explicitly applied only to currency marks. It must never lead the general UI font stack because its intentionally small glyph map can hide Latin characters.
- All font files are bundled locally for Console, Portal, Mobile Web, Android, and offline use.
- External Google Fonts requests are prohibited.

## Logo policy

- The DIGIT symbol geometry and wordmark are preserved from the official assets.
- The symbol is not redrawn, cropped, stretched, recolored outside the dark/light variants, or combined with a competing logo.
- Product differentiation is textual: “Field Service”, “Service Portal”, or “Field Console”.
- The app switcher, Desktop Icon, Android launcher, and Android splash use the official DIGIT symbol/wordmark.

## Surface ownership

| Surface | Identity treatment |
|---|---|
| Frappe app switcher | DIGIT app icon + DIGIT Field Service title |
| Desk Workspace | DIGIT fonts, brand controls, paper surface, emerald selection states |
| Desk sidebar | DIGIT accent, correct Field Service link grouping, official app icon |
| Console | Deep-green operations sidebar, paper default theme, DIGIT wordmark, shared language/theme state |
| Portal | Paper default theme, DIGIT Service Portal wordmark, same controls and typography |
| Mobile Web | Deep-green field surface, DIGIT wordmark, local fonts, RTL-aware directional controls |
| Android | DIGIT launcher icon, adaptive foreground/background, splash, status bar, notification color, visible app name |

## DIGIT shell integration

The technical Frappe app name remains `fsm` and is the installation-discovery key. When both `digit` and `fsm` are installed on the same site, the DIGIT backend adds one conditional **DIGIT Field Service** item to its workspace navigation, command palette, app switcher, and Connected Apps card. Every entry performs a full same-origin navigation to `/fsm-console/`; no FSM route is rendered inside or duplicated by the DIGIT SPA.

When `fsm` is not installed, the item is absent. This preserves independent installation and avoids a hard dependency between the two applications.

## Theme and localization contract

- Console and Portal share the `digit-theme` browser preference used by the DIGIT product.
- Light is the default for web surfaces; the deep-green operational theme remains available.
- Mobile Field App remains deep-green by design for outdoor contrast.
- Arabic uses `lang="ar"` and `dir="rtl"`; English uses `lang="en"` and `dir="ltr"`.
- Directional icons mirror in RTL; the DIGIT logo never mirrors.

## Change rules

1. Add or change identity tokens only in `frontend/design/tokens.json`.
2. Reuse the shared `DigitBrand` component; do not add page-specific logo drawings.
3. Do not introduce network font dependencies.
4. Do not use the primary mint as body text on paper without contrast validation.
5. Native launcher or splash updates must be derived from the official DIGIT assets.
6. Internal package names use `@digit/*`; the Android application ID is `com.digit.fsm`, and the offline database is `digit-fsm-field`. Future changes to these identifiers require an explicit migration decision.

## Verification contract

Before accepting an identity change, run from `frontend/` with Node 20 or newer:

```bash
yarn typecheck
yarn lint
yarn format:check
yarn test
yarn build
yarn test:e2e
```

For Android Debug, sync the final Mobile Web bundle before regenerating identity resources and assembling the APK:

```bash
npx cap sync android
yarn brand:android
cd android && ./gradlew assembleDebug
```

Release signing, AAB output, store metadata, and the absent iOS native shell remain separate delivery gates.

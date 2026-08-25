# Phase 14 — Arabic / RTL / UX — Gate Report

**Date:** 2026-08-25  
**Branch:** `develop`  
**Implementation base:** `a2830098289346d5f0d4b7df47562344a93d09d7`
**Evidence site:** `digit16.digit-erp.com`  
**Verdict:** **UX-RTL-GATE: PASS**

## Delivered

- Console, Portal and Mobile share one reactive Arabic/English locale contract and the `kl-lang`
  preference.
- Arabic is the clean-browser default; every surface applies the selected locale to the document
  `lang` and `dir` attributes.
- Portal and Mobile visible labels, navigation, errors, placeholders and accessibility names are
  bilingual. Brand names, document identifiers and server-owned business data intentionally remain
  literal.
- Statuses, dates, numbers and monetary values use locale-aware shared formatters.
- Direction-dependent spacing uses logical start/end behavior. The Ionic Mobile back affordance is
  mirrored in RTL.
- Forms retain appropriate input direction for email, telephone and technical identifiers while their
  surrounding layout follows the document direction.

## Verification evidence

| Check | Result |
|---|---|
| Frontend unit/component tests | **13/13 PASS** |
| Responsive E2E | **28/28 PASS** |
| E2E viewports | **390px and 1440px** |
| Arabic/English `lang` + `dir` switch | **PASS** |
| Portal/Mobile horizontal overflow assertion | **PASS** |
| TypeScript workspace typecheck | **PASS** |
| ESLint | **PASS** |
| Prettier check | **PASS** |
| Console production build | **PASS** |
| Portal production build | **PASS** |
| Mobile Web production build | **PASS** |
| Visible hardcoded-string audit | **PASS** — brand/technical/dynamic values only |
| Direction-specific utility audit | **PASS** |

The Mobile Web build emits Vite's advisory that one Ionic bundle is larger than 500 kB. This is a
non-blocking performance warning, not a build failure; bundle profiling remains part of Phase 15.

## Scope and release consequence

This gate changes frontend localization and presentation only. The last passing backend evidence remains
**141/141** from Phase 13; no backend schema or production environment was changed. Phase 15 is now
unlocked, but hardening, final UAT and signed Android release are separate gates and were not started by
this phase.

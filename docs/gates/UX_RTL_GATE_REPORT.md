# Phase 14 — Arabic / RTL / UX — Gate Report

**Date:** 2026-08-25  
**Branch:** `develop`  
**Pre-phase HEAD:** `b2b48eb`  
**Evidence site:** `digit16.digit-erp.com`  
**Verdict:** **UX-RTL-GATE: FAIL**

## Blocking evidence

The Console has an Arabic-first language state and applies `lang=ar` / `dir=rtl`, but the requirement covers all three surfaces. Portal and Mobile do not yet have a locale state or translation catalogue, and both entry documents currently declare `lang="en"`.

A static visible-text audit found:

| Surface | Visible hardcoded Latin-text candidates |
|---|---:|
| Portal Vue views | 60 |
| Mobile Vue views | 23 |

There are also 7 direction-specific layout utility occurrences (`ml`/`mr`/`left`/`right`) in Portal/Mobile that require logical-direction review. Status labels, validation feedback, dates, number formatting and accessibility labels need Arabic/English coverage at 390px, tablet and 1440px.

## Consequence

The binding acceptance condition “no visible untranslated hardcoded strings” is not met. Per PROJECT-COMPLETE stop policy, Phase 15 hardening, Phase 16 final UAT and Phase 17 final signed Android release are locked and were not started.

## Required closure work

1. Add one shared locale contract/catalogue used by Console, Portal and Mobile.
2. Convert all visible labels, errors, placeholders and accessibility strings.
3. Replace directional spacing/icons with logical RTL-safe behavior.
4. Add Arabic and English E2E assertions at 390px, tablet and 1440px.
5. Re-run full frontend/backend/E2E/build/migrate gate evidence.

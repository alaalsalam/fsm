# Mobile Bundle Review — Phase 15 Hardening

**Date:** 2026-08-25 · **Scope:** Mobile Web (Capacitor) build only. No Android release work.

## 1. Cause of the >500 kB warning

Before hardening, `frontend/mobile/vite.config.ts` had **no `manualChunks` policy** (unlike the
Console build), so the entire vendor graph — `@ionic/vue`, Vue, Pinia, Capacitor plugins and app
code — landed in a single `index-*.js` of **≈1.1 MB**.

## 2. Safe fix applied (build-config only)

Added the same vendor-split policy the Console build has used since IB (`manualChunks` in
`vite.config.ts`): `vendor-ionic`, `vendor-vue`, `vendor-capacitor`, `vendor` (misc), app `index`.
No app code, router, offline engine or architecture change. Views were already route-lazy.

### Result (after)

| Chunk | Raw | Gzip |
|---|---|---|
| `index` (app code) | **9.86 kB** (was ≈1.1 MB) | 4.13 kB |
| `vendor-vue` | 10.35 kB | 4.70 kB |
| `vendor-capacitor` | 17.10 kB | 6.11 kB |
| `vendor` (misc) | 41.19 kB | 12.87 kB |
| `vendor-ionic` | **1,147.35 kB** | **250.43 kB** |

## 3. Residual >500 kB chunk — classification

`vendor-ionic` remains over the warning limit because **`@ionic/vue`'s main export registers the
full Ionic component set by design**; it is a monolithic third-party artifact, not app code.

**Severity: LOW.** Justification:
- Capacitor packages `dist/` **inside the app binary** — the chunk is loaded from local disk, never
  over the network, so raw size does not affect field connectivity or the offline engine.
- Over-the-wire size (Mobile *Web* preview) is 250 kB gzip — an acceptable one-time cost, cached.
- Parse cost is paid once at app start; views and app logic are in separate small lazy chunks.
- The only further reduction path is rewriting every Ionic usage to per-component imports — an
  architecture redesign explicitly out of Phase 15 scope, with regression risk across all screens.

## 4. Offline-safety statement

Chunk splitting is neutral for the offline engine: all chunks ship in the same `dist/` that
Capacitor serves locally; the IndexedDB command queue and sync logic are unchanged and their unit
tests still pass (see HARDENING_REGRESSION_REPORT).

## 5. Decision

- ✅ Safe code-splitting applied (vendor split; app chunk now 9.9 kB).
- ✅ Residual `vendor-ionic` chunk documented and classified **LOW**; no further action in Phase 15.
- ❌ No `chunkSizeWarningLimit` suppression — the warning stays visible by design as evidence.
- ❌ No architecture redesign, no Ionic per-component rewrite, no Android build.

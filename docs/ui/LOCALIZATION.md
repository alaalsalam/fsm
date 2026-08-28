# Frontend Localization Contract

Console, Portal and Mobile use the shared helpers exported by `@digit/ui` from
`frontend/ui/src/i18n.ts`.

## Behavior

- Supported locales: Arabic (`ar`) and English (`en`).
- Default for a clean browser: Arabic.
- Persisted preference key: `kl-lang`.
- `initializeLocale()` restores the preference and applies `html[lang]`, `html[dir]` and `kl-rtl`.
- `setLocale()` and `toggleLocale()` are the only locale mutation entry points.
- `t(arabic, english)` provides reactive visible copy.
- `formatDate`, `formatNumber`, `formatMoney` and `statusLabel` provide locale-aware display values.

## UI rules

1. Do not add a user-visible string without Arabic and English variants.
2. Use logical `start`/`end` layout utilities; avoid hardcoded left/right positioning.
3. Mirror directional icons in RTL. Do not mirror non-directional symbols or product marks.
4. Preserve LTR input direction where the value is intrinsically LTR, such as email addresses,
   telephone numbers and technical IDs.
5. Keep server identifiers and user/business data literal; translate only their labels and known
   enumerated states.
6. Any new surface must test `lang`, `dir` and horizontal overflow at 390px and 1440px.

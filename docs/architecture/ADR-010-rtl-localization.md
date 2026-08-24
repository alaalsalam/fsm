# ADR-010: Arabic-first RTL and shared localization

- Status: Proposed
- Date: 2026-08-24

## Context

Console, Portal, and Mobile currently share tokens/components but are English-first. RTL cannot be achieved through text translation alone; direction, icons, gestures, maps, numbers, and mixed content need one policy.

## Decision

All user-visible strings use shared message keys with Arabic and English catalogues. Document direction derives from active locale. Components use logical CSS properties (`inline-start/end`) and direction-aware icons; semantic arrows/actions are mirrored while media, charts, maps, phone numbers, codes, and serials preserve appropriate LTR behavior.

Dates, numbers, currency, and relative time use locale-aware formatters, while stored values remain canonical. API errors return stable codes plus parameters; each surface localizes them. The shared design system supplies RTL component states and accessibility behavior.

## Consequences

- No hard-coded user-visible English/Arabic strings in views or backend responses.
- Console, Portal, and Mobile use the same glossary and status labels.
- Automated tests cover Arabic/English, narrow/wide layouts, keyboard order, screen readers, and screenshot diffs.
- Backend identifiers and event names remain English stable contracts.

## Approval gate

Approve glossary, locale fallback, status translations, typography, and RTL visual regression baseline before redesign or new screens.

# CORE gate final report

Date: 2026-08-24

Branch: `develop`

Approved pre-CORE HEAD: `536470e5f7596e2825804fa66f7a3fde9836631c`

## Decision

**CORE-GATE: PASS**, conditional only on the report commit itself and the final cleanup checks recorded at handoff. No subsequent feature phase is authorized by this decision.

## Acceptance evidence

| Gate | Result |
|---|---|
| Request replaces Appointment; no duplicate runtime DocType | PASS |
| Request 1:N Job; Job 1:N Visit | PASS, backend tests |
| command-owned lifecycle/checklist independence | PASS, controller and negative tests |
| append-only Event Log | PASS, create/update/delete negative tests |
| Customer/Technician/Manager/Guest boundaries | PASS |
| targeted/full backend | 13/13; 26/26 PASS |
| frontend unit/type/lint/format | 10/10; PASS |
| E2E | 12/12 PASS, 390px and 1440px |
| Console/Portal/Mobile web builds | PASS/PASS/PASS |
| Android debug | PASS; Java 17 build context, server default remains Java 11 |
| development migrate repeated | PASS/PASS; patch recorded, stable schema |
| production | untouched |

## Android artifact

Path: `frontend/mobile/android/app/build/outputs/apk/debug/app-debug.apk` (not committed)

Size: 8,570,620 bytes

SHA-256: `c0905816d6b23c9984ac4b91a43af4f53d38279f60fab4eea9a6ea0e6a627f61`

Toolchain: OpenJDK 17.0.19, Gradle 8.14.3, AGP 8.13.0, compile/target SDK 36. Default server Java before and after build: OpenJDK 11.0.24.

## Scope boundary

Installed Base, Teams, preventive maintenance, AMC, Workshop, offline, and RTL redesign were not started. SwiftService code was not copied. ERPNext remains the source of truth for commercial, stock, billing, and collection records.

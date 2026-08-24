# ADR-009: Offline mobile uses a command queue and server reconciliation

- Status: Accepted as target architecture
- Date: 2026-08-24

## Context

The current mobile app is an online SPA wrapper. Field execution needs intermittent-network tolerance without making the device a second source of truth.

## Decision

Cache assigned read models and queue explicit commands locally. Every queued command has a client-generated ID, aggregate ID/version, actor/device, timestamp, and payload schema version. The server is authoritative and deduplicates command IDs.

Safe append-only commands such as notes, photos, location events, and time events may synchronize automatically. State transitions and edits use optimistic aggregate versions; conflicts stop and appear in a Sync Issues screen. Financial, stock-posting, assignment, cancellation, and permission administration are never performed offline.

Local sensitive data is encrypted using platform keystore-backed secrets, minimized, and remotely revocable. API key/secret pairs are not the long-term device session design.

## Consequences

- “Offline” does not mean local CRUD mirroring.
- Mobile needs sync status, retry, conflict resolution, logout wipe, retention, and observability.
- Attachments use resumable/idempotent upload contracts.
- Server permissions are re-evaluated at sync time.

## Approval gate

Threat model, conflict matrix, storage/retention policy, token lifecycle, and offline acceptance tests must be approved before implementation.

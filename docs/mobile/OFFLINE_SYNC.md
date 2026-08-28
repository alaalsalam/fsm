# Mobile Offline Sync

## Local database

The Capacitor WebView uses IndexedDB database `digit-fsm-field` with separate `cache`, `commands`, and `media` stores. Jobs/equipment bundles, photos and signatures therefore survive reloads without relying on LocalStorage.

## Command envelope

Each command has a UUID `command_id`, entity type/id, optional `expected_version`, allowlisted action, payload, creation timestamp and one of `Queued`, `Syncing`, `Synced`, `Conflict`, or `Failed`.

On reconnect, at most 50 commands are sent to `fsm.offline.sync_commands`. The server:

1. authenticates a Technician/Manager;
2. validates the UUID, action/entity pairing and payload bound;
3. checks optimistic version where supplied;
4. invokes the existing guarded domain command;
5. stores one immutable `Mobile Command Receipt` for successful execution.

A retry of a successful UUID returns its prior result. A stale version returns `Conflict` without mutation. Failed commands remain visible and may be retried. No generic CRUD path is exposed.

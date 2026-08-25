import { client } from "./api";

export type SyncState = "Queued" | "Syncing" | "Synced" | "Conflict" | "Failed";

export interface OfflineCommand {
	command_id: string;
	entity_type: string;
	entity_id: string;
	expected_version?: string;
	action: string;
	payload: Record<string, unknown>;
	created_at: string;
	state: SyncState;
	error?: string;
}

const DB_NAME = "kodlyft-fsm-field";
const DB_VERSION = 1;

function database(): Promise<IDBDatabase> {
	return new Promise((resolve, reject) => {
		const request = indexedDB.open(DB_NAME, DB_VERSION);
		request.onupgradeneeded = () => {
			const db = request.result;
			if (!db.objectStoreNames.contains("cache")) db.createObjectStore("cache");
			if (!db.objectStoreNames.contains("commands")) {
				const store = db.createObjectStore("commands", { keyPath: "command_id" });
				store.createIndex("state", "state");
			}
			if (!db.objectStoreNames.contains("media")) db.createObjectStore("media");
		};
		request.onsuccess = () => resolve(request.result);
		request.onerror = () => reject(request.error);
	});
}

async function transact<T>(
	store: string,
	mode: IDBTransactionMode,
	run: (s: IDBObjectStore) => IDBRequest<T>,
) {
	const db = await database();
	return new Promise<T>((resolve, reject) => {
		const tx = db.transaction(store, mode);
		const request = run(tx.objectStore(store));
		request.onsuccess = () => resolve(request.result);
		request.onerror = () => reject(request.error);
		tx.oncomplete = () => db.close();
	});
}

export function createOfflineCommand(
	values: Omit<OfflineCommand, "command_id" | "created_at" | "state">,
): OfflineCommand {
	return {
		...values,
		command_id: crypto.randomUUID(),
		created_at: new Date().toISOString(),
		state: "Queued",
	};
}

export async function cachePut(key: string, value: unknown) {
	await transact("cache", "readwrite", (store) =>
		store.put({ value, saved_at: new Date().toISOString() }, key),
	);
}

export async function cacheGet<T>(key: string): Promise<T | undefined> {
	const row = await transact<{ value: T } | undefined>("cache", "readonly", (store) =>
		store.get(key),
	);
	return row?.value;
}

export async function mediaPut(key: string, value: Blob | string) {
	await transact("media", "readwrite", (store) => store.put(value, key));
}

export async function mediaGet(key: string): Promise<Blob | string | undefined> {
	return transact("media", "readonly", (store) => store.get(key));
}

export async function enqueue(command: OfflineCommand) {
	await transact("commands", "readwrite", (store) => store.put(command));
	return command;
}

export async function listCommands(): Promise<OfflineCommand[]> {
	return transact("commands", "readonly", (store) => store.getAll());
}

async function saveCommand(command: OfflineCommand) {
	await transact("commands", "readwrite", (store) => store.put(command));
}

export async function retryCommand(commandId: string) {
	const command = await transact<OfflineCommand | undefined>("commands", "readonly", (store) =>
		store.get(commandId),
	);
	if (command) await saveCommand({ ...command, state: "Queued", error: undefined });
}

export async function syncQueued(): Promise<OfflineCommand[]> {
	const pending = (await listCommands())
		.filter((row) => row.state === "Queued" || row.state === "Failed")
		.slice(0, 50);
	if (!pending.length) return listCommands();
	for (const row of pending) await saveCommand({ ...row, state: "Syncing" });
	try {
		const response = await client.call<{
			results: Array<{ command_id: string; state: SyncState; error?: string }>;
		}>("fsm.offline.sync_commands", { commands: pending });
		for (const result of response.results) {
			const source = pending.find((row) => row.command_id === result.command_id);
			if (source) await saveCommand({ ...source, state: result.state, error: result.error });
		}
	} catch (error) {
		for (const row of pending)
			await saveCommand({ ...row, state: "Failed", error: String(error) });
	}
	return listCommands();
}

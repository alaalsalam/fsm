import { describe, expect, it, vi } from "vitest";
import { createOfflineCommand, isPrunable, orderForSync, type OfflineCommand } from "./offline";

function command(overrides: Partial<OfflineCommand>): OfflineCommand {
	return {
		command_id: overrides.command_id ?? crypto.randomUUID(),
		entity_type: "Service Visit",
		entity_id: "VIS-1",
		action: "visit.start_travel",
		payload: {},
		created_at: "2026-08-25T10:00:00.000Z",
		state: "Queued",
		...overrides,
	};
}

describe("offline command envelope", () => {
	it("creates a durable, retry-safe command identity", () => {
		vi.stubGlobal("crypto", { randomUUID: () => "11111111-1111-4111-8111-111111111111" });
		const created = createOfflineCommand({
			entity_type: "Service Visit",
			entity_id: "VIS-1",
			expected_version: "2026-08-25 10:00:00",
			action: "visit.start_travel",
			payload: {},
		});
		expect(created.command_id).toBe("11111111-1111-4111-8111-111111111111");
		expect(created.state).toBe("Queued");
		expect(created.entity_type).toBe("Service Visit");
	});
});

describe("sync batch ordering", () => {
	it("submits in capture order regardless of random key order", () => {
		const rows = [
			command({ command_id: "c", created_at: "2026-08-25T10:03:00.000Z" }),
			command({ command_id: "a", created_at: "2026-08-25T10:01:00.000Z" }),
			command({ command_id: "b", created_at: "2026-08-25T10:02:00.000Z", state: "Failed" }),
			command({ command_id: "d", created_at: "2026-08-25T10:00:00.000Z", state: "Synced" }),
		];
		expect(orderForSync(rows).map((row) => row.command_id)).toEqual(["a", "b", "c"]);
	});

	it("bounds a batch to 50 commands", () => {
		const rows = Array.from({ length: 60 }, (_, i) =>
			command({
				command_id: `id-${i}`,
				created_at: `2026-08-25T10:00:${String(i).padStart(2, "0")}.000Z`,
			}),
		);
		expect(orderForSync(rows)).toHaveLength(50);
	});
});

describe("synced command pruning", () => {
	const now = Date.parse("2026-09-10T00:00:00.000Z");

	it("prunes only aged Synced commands", () => {
		expect(isPrunable(command({ state: "Synced" }), now)).toBe(true);
		expect(isPrunable(command({ state: "Queued" }), now)).toBe(false);
		expect(isPrunable(command({ state: "Failed" }), now)).toBe(false);
		expect(isPrunable(command({ state: "Conflict" }), now)).toBe(false);
	});

	it("keeps recently synced commands inside the retention window", () => {
		const recent = command({ state: "Synced", created_at: "2026-09-09T00:00:00.000Z" });
		expect(isPrunable(recent, now)).toBe(false);
	});
});

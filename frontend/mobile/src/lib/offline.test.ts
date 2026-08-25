import { describe, expect, it, vi } from "vitest";
import { createOfflineCommand } from "./offline";

describe("offline command envelope", () => {
	it("creates a durable, retry-safe command identity", () => {
		vi.stubGlobal("crypto", { randomUUID: () => "11111111-1111-4111-8111-111111111111" });
		const command = createOfflineCommand({
			entity_type: "Service Visit",
			entity_id: "VIS-1",
			expected_version: "2026-08-25 10:00:00",
			action: "visit.start_travel",
			payload: {},
		});
		expect(command.command_id).toBe("11111111-1111-4111-8111-111111111111");
		expect(command.state).toBe("Queued");
		expect(command.entity_type).toBe("Service Visit");
	});
});

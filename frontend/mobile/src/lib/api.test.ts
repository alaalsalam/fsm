import { describe, expect, it, vi } from "vitest";

import { client } from "./api";

describe("mobile API failures", () => {
	it("surfaces offline fetch failures", async () => {
		vi.stubGlobal("fetch", vi.fn().mockRejectedValueOnce(new TypeError("offline")));
		await expect(client.call("fsm.api.get_dispatch_jobs", {}, "GET")).rejects.toThrow(
			"offline",
		);
	});
});

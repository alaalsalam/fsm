import { describe, expect, it, vi } from "vitest";

import { client, getJobMessages } from "./api";

describe("portal API failures", () => {
	it("does not swallow a forbidden job response", async () => {
		vi.spyOn(client, "call").mockRejectedValueOnce(new Error("403 forbidden"));
		await expect(getJobMessages("JOB-OTHER-CUSTOMER")).rejects.toThrow("403 forbidden");
	});
});

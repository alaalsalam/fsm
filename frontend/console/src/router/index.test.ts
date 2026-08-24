import { describe, expect, it } from "vitest";

import { authGuardDecision } from "./index";

describe("console route authorization", () => {
	it("redirects an anonymous protected route to login", () => {
		expect(authGuardDecision(false, false, false, "/jobs")).toEqual({
			name: "login",
			query: { redirect: "/jobs" },
		});
	});

	it("keeps authenticated users out of the login page", () => {
		expect(authGuardDecision(true, true, true, "/login")).toEqual({ path: "/" });
	});
});

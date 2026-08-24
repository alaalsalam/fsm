import { describe, expect, it } from "vitest";

import { portalGuardDecision } from "./index";

describe("portal route authorization", () => {
	it("redirects an anonymous account request", () => {
		expect(portalGuardDecision(true, false, false, "/account")).toEqual({
			name: "login",
			query: { redirect: "/account" },
		});
	});

	it("redirects a signed-in customer away from auth screens", () => {
		expect(portalGuardDecision(false, true, true, "/signup")).toEqual({ name: "account" });
	});
});

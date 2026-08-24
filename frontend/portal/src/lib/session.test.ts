import { beforeEach, describe, expect, it, vi } from "vitest";

const { getSession } = vi.hoisted(() => ({ getSession: vi.fn() }));
vi.mock("./api", () => ({
	getSession,
	login: vi.fn(),
	logout: vi.fn(),
	registerCustomer: vi.fn(),
}));

import { loadSession, session } from "./session";

describe("portal session", () => {
	beforeEach(() => getSession.mockReset());

	it("fails closed when session loading fails", async () => {
		getSession.mockRejectedValueOnce(new Error("offline"));
		await loadSession(true);
		expect(session.ready).toBe(true);
		expect(session.session.authenticated).toBe(false);
	});
});

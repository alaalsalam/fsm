import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { session } = vi.hoisted(() => ({ session: vi.fn() }));
vi.mock("@/lib/api", () => ({ auth: { session, login: vi.fn(), logout: vi.fn() } }));

import { useAuthStore } from "./auth";

describe("console auth store", () => {
	beforeEach(() => setActivePinia(createPinia()));

	it("fails closed when the session API fails", async () => {
		session.mockRejectedValueOnce(new Error("network unavailable"));
		const store = useAuthStore();
		await store.load();
		expect(store.ready).toBe(true);
		expect(store.isAuthenticated).toBe(false);
	});
});

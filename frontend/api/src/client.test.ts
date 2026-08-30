import { describe, expect, it } from "vitest";
import { extractFrappeErrorMessage } from "./client";

describe("Frappe error messages", () => {
	it("extracts validation messages from Frappe server messages", () => {
		const message = extractFrappeErrorMessage({
			_server_messages: JSON.stringify([
				JSON.stringify({ message: "Confirm the installation site first." }),
			]),
			exception: "frappe.exceptions.ValidationError",
		});
		expect(message).toBe("Confirm the installation site first.");
	});

	it("falls back to the response message and exception", () => {
		expect(extractFrappeErrorMessage({ message: "Not permitted" })).toBe("Not permitted");
		expect(extractFrappeErrorMessage({ exception: "ValidationError" })).toBe("ValidationError");
	});
});

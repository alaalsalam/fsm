import { beforeEach, describe, expect, it } from "vitest";
import { initializeLocale, locale, setLocale, statusLabel, t } from "./i18n";

describe("shared Arabic/English locale", () => {
	beforeEach(() => {
		setLocale("ar");
	});

	it("defaults to Arabic and translates domain states", () => {
		initializeLocale("ar");
		expect(locale.value).toBe("ar");
		expect(t("العربية", "English")).toBe("العربية");
		expect(statusLabel("In Progress")).toBe("قيد التنفيذ");
	});

	it("switches to English without changing domain values", () => {
		setLocale("en");
		expect(t("العربية", "English")).toBe("English");
		expect(statusLabel("In Progress")).toBe("In Progress");
	});
});

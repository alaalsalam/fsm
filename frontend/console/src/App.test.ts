import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import App from "./App.vue";

describe("console application", () => {
	it("boots its router outlet", () => {
		const wrapper = mount(App, {
			global: { stubs: { RouterView: { template: "<main data-router-view />" } } },
		});
		expect(wrapper.find("[data-router-view]").exists()).toBe(true);
	});
});

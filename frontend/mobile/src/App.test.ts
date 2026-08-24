import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import App from "./App.vue";

describe("mobile application", () => {
	it("boots the Ionic router outlet", () => {
		const wrapper = mount(App, {
			global: {
				stubs: {
					IonApp: { template: "<div data-ion-app><slot /></div>" },
					IonRouterOutlet: { template: "<main data-router-outlet />" },
				},
			},
		});
		expect(wrapper.find("[data-ion-app]").exists()).toBe(true);
		expect(wrapper.find("[data-router-outlet]").exists()).toBe(true);
	});
});

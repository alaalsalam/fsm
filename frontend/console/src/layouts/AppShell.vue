<script setup lang="ts">
import { computed } from "vue";
import { RouterView, RouterLink, useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { theme, toggleTheme } from "@/lib/theme";
import { lang, toggleLang, t } from "@/lib/i18n";
import { DigitBrand } from "@kodlyft/ui";
import ConsoleNavIcon from "@/components/ConsoleNavIcon.vue";

const store = useAuthStore();
const router = useRouter();

const nav = computed(() => [
	{ name: "operations", label: t("مركز العمليات", "Operations"), to: "/", exact: true },
	{ name: "dispatch", label: t("لوحة التوزيع", "Dispatch"), to: "/dispatch", exact: true },
	{ name: "requests", label: t("الطلبات", "Requests"), to: "/requests", exact: false },
	{ name: "jobs", label: t("أوامر العمل", "Jobs"), to: "/jobs", exact: false },
	{ name: "visits", label: t("الزيارات", "Visits"), to: "/visits", exact: false },
	{ name: "exceptions", label: t("الاستثناءات", "Exceptions"), to: "/exceptions", exact: false },
	{
		name: "after-sales",
		label: t("إعداد ما بعد البيع", "After-sales setup"),
		to: "/after-sales",
		exact: false,
	},
	{ name: "equipment", label: t("المعدات", "Equipment"), to: "/equipment", exact: false },
	{
		name: "customer-360",
		label: t("العميل 360", "Customer 360"),
		to: "/customers",
		exact: false,
	},
	{ name: "sites", label: t("المواقع", "Sites"), to: "/sites", exact: false },
	{ name: "contracts", label: t("العقود", "Contracts"), to: "/contracts", exact: false },
	{
		name: "maintenance",
		label: t("الصيانة الوقائية", "Maintenance"),
		to: "/maintenance",
		exact: false,
	},
	{
		name: "equipment-locations",
		label: t("المواضع", "Locations"),
		to: "/equipment-locations",
		exact: false,
	},
	{ name: "inventory", label: t("المخزون", "Inventory"), to: "/inventory", exact: false },
	{ name: "returns", label: t("المرتجعات", "Returns"), to: "/returns", exact: false },
	{
		name: "subcontractors",
		label: t("الشركاء", "Partners"),
		to: "/subcontractors",
		exact: false,
	},
	{ name: "analytics", label: t("التحليلات", "Analytics"), to: "/analytics", exact: false },
	{
		name: "integrations",
		label: t("التكاملات", "Integrations"),
		to: "/integrations",
		exact: false,
	},
	{ name: "account", label: t("الحساب", "Account"), to: "/account", exact: false },
]);

const mobileNav = computed(() =>
	nav.value.filter((item) =>
		["operations", "dispatch", "requests", "jobs", "account"].includes(item.name),
	),
);

const displayName = computed(() => store.user?.full_name ?? store.user?.name ?? "");
const initials = computed(() =>
	displayName.value
		.split(/\s+/)
		.filter(Boolean)
		.slice(0, 2)
		.map((p) => p[0]?.toUpperCase())
		.join(""),
);

async function signOut() {
	await store.logout();
	router.push({ name: "login" });
}
</script>

<template>
	<div class="kl-command flex min-h-screen">
		<aside class="sticky top-0 hidden h-screen w-64 shrink-0 flex-col p-4 md:flex">
			<div class="digit-sidebar kl-glass flex h-full flex-col rounded-2xl p-4">
				<div class="mb-7 px-1">
					<DigitBrand compact tone="light" :locale="lang" />
					<p class="mt-1 text-xs font-medium text-cmd-fg-muted">
						{{ t("الخدمة الميدانية", "Field Service") }}
					</p>
				</div>

				<nav class="flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto pe-1">
					<RouterLink
						v-for="item in nav"
						:key="item.name"
						:to="item.to"
						class="group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-cmd-fg-muted transition-colors duration-200 hover:bg-white/5 hover:text-cmd-fg"
						:active-class="item.exact ? '' : 'nav-active'"
						:exact-active-class="item.exact ? 'nav-active' : ''"
					>
						<ConsoleNavIcon :name="item.name" class="size-5 shrink-0" />
						<span>{{ item.label }}</span>
					</RouterLink>
				</nav>

				<div class="mt-3 space-y-2">
					<!-- Language toggle -->
					<button
						type="button"
						class="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-cmd-fg-muted transition-colors hover:bg-white/5 hover:text-cmd-fg"
						:aria-label="lang === 'ar' ? 'Switch to English' : 'التبديل إلى العربية'"
						@click="toggleLang"
					>
						<svg
							viewBox="0 0 24 24"
							class="size-5 shrink-0"
							fill="none"
							stroke="currentColor"
							stroke-width="1.8"
							stroke-linecap="round"
							stroke-linejoin="round"
							aria-hidden="true"
						>
							<circle cx="12" cy="12" r="9" />
							<path d="M3 12h18M12 3c-2.5 4-2.5 14 0 18M12 3c2.5 4 2.5 14 0 18" />
						</svg>
						<span>{{ lang === "ar" ? "English" : "العربية" }}</span>
					</button>

					<!-- Theme toggle -->
					<button
						type="button"
						class="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-cmd-fg-muted transition-colors hover:bg-white/5 hover:text-cmd-fg"
						@click="toggleTheme"
					>
						<svg
							viewBox="0 0 24 24"
							class="size-5 shrink-0"
							fill="none"
							stroke="currentColor"
							stroke-width="1.8"
							stroke-linecap="round"
							stroke-linejoin="round"
							aria-hidden="true"
						>
							<template v-if="theme === 'dark'">
								<circle cx="12" cy="12" r="4" />
								<path
									d="M12 2v2M12 20v2M4 12H2M22 12h-2M5 5l1.5 1.5M17.5 17.5 19 19M19 5l-1.5 1.5M6.5 17.5 5 19"
								/>
							</template>
							<template v-else>
								<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
							</template>
						</svg>
						<span>{{
							theme === "dark"
								? t("الوضع الفاتح", "Light mode")
								: t("الوضع الداكن", "Dark mode")
						}}</span>
					</button>

					<RouterLink
						to="/account"
						class="flex items-center gap-3 rounded-xl border border-cmd-border bg-white/3 p-3 transition-colors hover:bg-white/6"
					>
						<span
							class="kl-grad-brand flex size-9 shrink-0 items-center justify-center rounded-full text-sm font-bold text-white"
						>
							{{ initials || "·" }}
						</span>
						<div class="min-w-0 flex-1">
							<p class="truncate text-sm font-medium text-cmd-fg">
								{{ displayName }}
							</p>
							<p class="truncate text-xs text-cmd-fg-muted">
								{{ t("عرض الحساب", "View account") }}
							</p>
						</div>
					</RouterLink>
				</div>
			</div>
		</aside>

		<div class="flex min-w-0 flex-1 flex-col">
			<header
				class="kl-glass sticky top-0 z-20 flex items-center justify-between px-4 py-3 md:hidden"
			>
				<div class="flex items-center gap-2.5">
					<DigitBrand
						compact
						:locale="lang"
						:tone="theme === 'light' ? 'dark' : 'light'"
					/>
				</div>
				<div class="flex items-center gap-2">
					<button
						type="button"
						class="flex size-9 items-center justify-center rounded-full bg-white/5 text-xs font-bold text-cmd-fg"
						:aria-label="lang === 'ar' ? 'Switch to English' : 'التبديل إلى العربية'"
						@click="toggleLang"
					>
						{{ lang === "ar" ? "EN" : "ع" }}
					</button>
					<button
						type="button"
						class="flex size-9 items-center justify-center rounded-full bg-white/5 text-cmd-fg"
						:aria-label="
							theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'
						"
						@click="toggleTheme"
					>
						<svg
							viewBox="0 0 24 24"
							class="size-5"
							fill="none"
							stroke="currentColor"
							stroke-width="1.8"
							stroke-linecap="round"
							stroke-linejoin="round"
							aria-hidden="true"
						>
							<template v-if="theme === 'dark'">
								<circle cx="12" cy="12" r="4" />
								<path
									d="M12 2v2M12 20v2M4 12H2M22 12h-2M5 5l1.5 1.5M17.5 17.5 19 19M19 5l-1.5 1.5M6.5 17.5 5 19"
								/>
							</template>
							<template v-else>
								<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
							</template>
						</svg>
					</button>
					<button
						type="button"
						class="flex size-9 items-center justify-center rounded-full bg-white/5 text-sm font-bold text-cmd-fg"
						aria-label="Sign out"
						@click="signOut"
					>
						{{ initials || "·" }}
					</button>
				</div>
			</header>

			<main class="flex-1 overflow-auto p-4 pb-28 sm:p-6 md:pb-6">
				<RouterView />
			</main>

			<nav
				class="kl-glass fixed inset-x-3 bottom-3 z-30 flex items-center justify-around rounded-2xl px-2 py-2 md:hidden"
				style="padding-bottom: calc(0.5rem + env(safe-area-inset-bottom))"
			>
				<RouterLink
					v-for="item in mobileNav"
					:key="item.name"
					:to="item.to"
					class="flex flex-1 flex-col items-center gap-1 rounded-xl py-1.5 text-xs font-medium text-cmd-fg-muted transition-colors"
					:active-class="item.exact ? '' : 'tab-active'"
					:exact-active-class="item.exact ? 'tab-active' : ''"
				>
					<ConsoleNavIcon :name="item.name" class="size-5" />
					<span>{{ item.label }}</span>
				</RouterLink>
			</nav>
		</div>
	</div>
</template>

<style scoped>
.nav-active {
	background-image: var(--kl-grad-brand);
	color: #fff;
	box-shadow: var(--kl-elevation-e2);
}
.tab-active {
	color: var(--kl-cmd-brand);
}

.digit-sidebar {
	--color-cmd-fg: #f4f3ee;
	--color-cmd-fg-muted: #c7d5ce;
	--color-cmd-brand: #34d399;
	--color-cmd-border: rgba(52, 211, 153, 0.18);
	--color-cmd-border-strong: rgba(52, 211, 153, 0.3);
	--kl-cmd-glass: rgba(255, 255, 255, 0.06);
	--kl-cmd-glass-strong: rgba(255, 255, 255, 0.1);
	--kl-cmd-glass-border: rgba(52, 211, 153, 0.15);
	--kl-cmd-glass-border-strong: rgba(52, 211, 153, 0.28);
	--kl-cmd-text: #f4f3ee;
	--kl-cmd-text-muted: #b8c8c0;
	--kl-cmd-brand: #34d399;
	background-color: #064e3b;
	background-image: linear-gradient(180deg, #064e3b 0%, #06402f 100%);
	box-shadow: 0 20px 46px -28px rgba(3, 45, 35, 0.88);
}
</style>

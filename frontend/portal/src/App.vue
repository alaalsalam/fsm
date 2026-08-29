<script setup lang="ts">
import { onMounted } from "vue";
import { RouterView, RouterLink, useRouter } from "vue-router";
import { session, loadSession, signOut } from "@/lib/session";
import { theme, toggleTheme } from "@/lib/theme";
import { DigitBrand, locale, t, toggleLocale } from "@digit/ui";

const router = useRouter();

onMounted(() => loadSession());

async function handleSignOut() {
	await signOut();
	router.push({ name: "book" });
}
</script>

<template>
	<div class="kl-command flex min-h-screen flex-col">
		<header class="sticky top-0 z-20">
			<div
				class="kl-glass mx-auto mt-3 flex max-w-6xl items-center justify-between rounded-2xl px-4 py-3"
			>
				<RouterLink to="/" class="flex items-center gap-2.5">
					<DigitBrand
						:locale="locale"
						:tone="theme === 'light' ? 'dark' : 'light'"
						product-ar="بوابة الخدمة"
						product-en="Service Portal"
					/>
				</RouterLink>

				<nav class="flex items-center gap-1 text-sm sm:gap-2">
					<button
						type="button"
						class="rounded-lg px-2 py-1.5 font-semibold text-brand"
						:aria-label="t('تغيير اللغة إلى الإنجليزية', 'Switch language to Arabic')"
						@click="toggleLocale"
					>
						{{ locale === "ar" ? "EN" : "ع" }}
					</button>
					<button
						type="button"
						class="flex size-9 items-center justify-center rounded-lg text-cmd-fg-muted transition-colors hover:bg-white/5 hover:text-cmd-fg"
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
					<template v-if="session.session.authenticated">
						<RouterLink
							to="/dashboard"
							class="hidden rounded-lg px-2 py-1.5 font-medium text-cmd-fg-muted transition-colors hover:text-cmd-fg sm:inline-flex"
							>{{ t("لوحة التحكم", "Dashboard") }}</RouterLink
						>
						<RouterLink
							to="/my-sites"
							class="hidden rounded-lg px-2 py-1.5 font-medium text-cmd-fg-muted transition-colors hover:text-cmd-fg sm:inline-flex"
							>{{ t("المواقع", "Sites") }}</RouterLink
						>
						<RouterLink
							to="/my-schedule"
							class="hidden rounded-lg px-2 py-1.5 font-medium text-cmd-fg-muted transition-colors hover:text-cmd-fg sm:inline-flex"
							>{{ t("جدول الصيانة", "Schedule") }}</RouterLink
						>
						<RouterLink
							to="/my-services"
							class="hidden rounded-lg px-2 py-1.5 font-medium text-cmd-fg-muted transition-colors hover:text-cmd-fg sm:inline-flex"
							>{{ t("الخدمات", "Services") }}</RouterLink
						>
						<RouterLink
							to="/my-equipment"
							class="hidden rounded-lg px-2 py-1.5 font-medium text-cmd-fg-muted transition-colors hover:text-cmd-fg sm:inline-flex"
							>{{ t("المعدات", "Equipment") }}</RouterLink
						>
						<RouterLink
							to="/account"
							class="rounded-lg px-3 py-1.5 font-medium text-cmd-fg-muted transition-colors hover:text-cmd-fg"
							active-class="text-cmd-fg"
						>
							{{ t("حسابي", "My account") }}
						</RouterLink>
						<button
							type="button"
							class="rounded-lg px-3 py-1.5 font-medium text-cmd-fg-muted transition-colors hover:text-cmd-fg"
							@click="handleSignOut"
						>
							{{ t("تسجيل الخروج", "Sign out") }}
						</button>
					</template>
					<template v-else>
						<RouterLink
							to="/login"
							class="rounded-lg px-3 py-1.5 font-medium text-cmd-fg-muted transition-colors hover:text-cmd-fg"
						>
							{{ t("تسجيل الدخول", "Sign in") }}
						</RouterLink>
						<RouterLink
							to="/signup"
							class="kl-grad-brand rounded-lg px-3.5 py-1.5 font-semibold text-white shadow-e2 transition-[filter] hover:brightness-110"
						>
							{{ t("إنشاء حساب", "Sign up") }}
						</RouterLink>
					</template>
				</nav>
			</div>
		</header>

		<main class="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
			<RouterView />
		</main>

		<nav
			v-if="session.session.authenticated"
			class="kl-glass fixed inset-x-3 bottom-3 z-30 grid grid-cols-4 rounded-2xl p-1.5 shadow-glass sm:hidden"
			:aria-label="t('التنقل الرئيسي', 'Main navigation')"
		>
			<RouterLink
				v-for="item in [
					{ to: '/dashboard', ar: 'الرئيسية', en: 'Home' },
					{ to: '/my-schedule', ar: 'الجدول', en: 'Schedule' },
					{ to: '/my-services', ar: 'الخدمات', en: 'Services' },
					{ to: '/my-equipment', ar: 'المعدات', en: 'Equipment' },
				]"
				:key="item.to"
				:to="item.to"
				class="rounded-xl px-1 py-2 text-center text-xs font-medium text-cmd-fg-muted"
				active-class="bg-brand/10 text-brand"
			>
				{{ t(item.ar, item.en) }}
			</RouterLink>
		</nav>

		<footer
			class="mx-auto mb-20 flex w-full max-w-6xl flex-col items-center justify-between gap-2 px-4 py-6 text-sm text-cmd-fg-muted sm:mb-0 sm:flex-row"
		>
			<span dir="ltr">© DIGIT</span>
			<span>{{ t("خدمة ميدانية سريعة وموثوقة.", "Fast, friendly field service.") }}</span>
		</footer>
	</div>
</template>

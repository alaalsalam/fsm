import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";
import { loadSession, session } from "@/lib/session";

const routes: RouteRecordRaw[] = [
	{ path: "/", name: "book", component: () => import("@/views/BookingView.vue") },
	{ path: "/signup", name: "signup", component: () => import("@/views/SignupView.vue") },
	{ path: "/login", name: "login", component: () => import("@/views/LoginView.vue") },
	{
		path: "/dashboard",
		name: "dashboard",
		component: () => import("@/views/HubView.vue"),
		meta: { auth: true },
	},
	{
		path: "/account",
		name: "account",
		component: () => import("@/views/AccountView.vue"),
		meta: { auth: true },
	},
	{
		path: "/my-sites",
		name: "my-sites",
		component: () => import("@/views/MySitesView.vue"),
		meta: { auth: true },
	},
	{
		path: "/my-equipment",
		name: "my-equipment",
		component: () => import("@/views/MyEquipmentView.vue"),
		meta: { auth: true },
	},
	{
		path: "/my-schedule",
		name: "my-schedule",
		component: () => import("@/views/MyScheduleView.vue"),
		meta: { auth: true },
	},
	{
		path: "/my-services",
		name: "my-services",
		component: () => import("@/views/MyServicesView.vue"),
		meta: { auth: true },
	},
	{
		path: "/my-equipment/:name",
		name: "my-equipment-detail",
		component: () => import("@/views/MyEquipmentDetailView.vue"),
		props: true,
		meta: { auth: true },
	},
	{
		path: "/track/:job",
		name: "track",
		component: () => import("@/views/TrackView.vue"),
		props: true,
	},
];

const base = import.meta.env.DEV ? "/" : "/book/";

const router = createRouter({
	history: createWebHistory(base),
	routes,
});

export function portalGuardDecision(
	requiresAuth: boolean,
	isAuthEntry: boolean,
	isAuthenticated: boolean,
	fullPath: string,
) {
	if (requiresAuth && !isAuthenticated) {
		return { name: "login", query: { redirect: fullPath } };
	}
	if (isAuthEntry && isAuthenticated) return { name: "account" };
	return true;
}

router.beforeEach(async (to) => {
	await loadSession();
	return portalGuardDecision(
		Boolean(to.meta.auth),
		to.name === "login" || to.name === "signup",
		session.session.authenticated,
		to.fullPath,
	);
});

export default router;

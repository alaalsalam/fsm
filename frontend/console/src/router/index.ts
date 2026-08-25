import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const routes: RouteRecordRaw[] = [
	{
		path: "/login",
		name: "login",
		component: () => import("@/views/LoginView.vue"),
		meta: { public: true },
	},
	{
		path: "/",
		component: () => import("@/layouts/AppShell.vue"),
		children: [
			{
				path: "/",
				name: "dispatch",
				component: () => import("@/views/DispatchBoardView.vue"),
			},
			{ path: "/jobs", name: "jobs", component: () => import("@/views/JobsView.vue") },
			{
				path: "/contracts",
				name: "contracts",
				component: () => import("@/views/ContractsView.vue"),
			},
			{
				path: "/sites",
				name: "sites",
				component: () => import("@/views/CustomerSitesView.vue"),
			},
			{
				path: "/sites/:name",
				name: "site-detail",
				component: () => import("@/views/CustomerSiteDetailView.vue"),
				props: true,
			},
			{
				path: "/equipment",
				name: "equipment",
				component: () => import("@/views/InstalledEquipmentView.vue"),
			},
			{
				path: "/equipment/:name",
				name: "equipment-detail",
				component: () => import("@/views/InstalledEquipmentDetailView.vue"),
				props: true,
			},
			{
				path: "/equipment-locations",
				name: "equipment-locations",
				component: () => import("@/views/EquipmentLocationsView.vue"),
			},
			{
				path: "/requests",
				name: "requests",
				component: () => import("@/views/RequestsView.vue"),
			},
			{
				path: "/requests/:name",
				name: "request-detail",
				component: () => import("@/views/RequestDetailView.vue"),
				props: true,
			},
			{
				path: "/jobs/new",
				name: "job-new",
				component: () => import("@/views/NewJobView.vue"),
			},
			{
				path: "/jobs/:name",
				name: "job-detail",
				component: () => import("@/views/JobDetailView.vue"),
				props: true,
			},
			{
				path: "/inventory",
				name: "inventory",
				component: () => import("@/views/InventoryView.vue"),
			},
			{
				path: "/returns",
				name: "returns",
				component: () => import("@/views/ReturnsView.vue"),
			},
			{
				path: "/subcontractors",
				name: "subcontractors",
				component: () => import("@/views/SubcontractorsView.vue"),
			},
			{
				path: "/analytics",
				name: "analytics",
				component: () => import("@/views/AnalyticsView.vue"),
			},
			{
				path: "/integrations",
				name: "integrations",
				component: () => import("@/views/IntegrationsView.vue"),
			},
			{
				path: "/account",
				name: "account",
				component: () => import("@/views/AccountView.vue"),
			},
		],
	},
];

const router = createRouter({
	history: createWebHistory("/fsm-console/"),
	routes,
});

export function authGuardDecision(
	isPublic: boolean,
	isLogin: boolean,
	isAuthenticated: boolean,
	fullPath: string,
) {
	if (!isPublic && !isAuthenticated) {
		return { name: "login", query: { redirect: fullPath } };
	}
	if (isLogin && isAuthenticated) return { path: "/" };
	return true;
}

router.beforeEach(async (to) => {
	const store = useAuthStore();
	if (!store.ready) await store.load();
	return authGuardDecision(
		Boolean(to.meta.public),
		to.name === "login",
		store.isAuthenticated,
		to.fullPath,
	);
});

export default router;

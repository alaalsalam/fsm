<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { PageHeader, Spinner, StatusPill, formatDate } from "@digit/ui";
import { getScheduleBoard, type ScheduleBoard } from "@/lib/fsm";
import { lang, t } from "@/lib/i18n";

type ViewMode = "calendar" | "agenda" | "resources";
const board = ref<ScheduleBoard | null>(null);
const loading = ref(true);
const error = ref("");
const view = ref<ViewMode>("calendar");
const cursor = ref(new Date());
const teamFilter = ref("");
const query = ref("");

function iso(date: Date) {
	return date.toISOString().slice(0, 10);
}
const weekDays = computed(() => {
	const start = new Date(cursor.value);
	start.setDate(start.getDate() - ((start.getDay() + 6) % 7));
	return Array.from({ length: 7 }, (_, index) => {
		const day = new Date(start);
		day.setDate(start.getDate() + index);
		return day;
	});
});

async function load() {
	loading.value = true;
	error.value = "";
	try {
		board.value = await getScheduleBoard(iso(weekDays.value[0]), iso(weekDays.value[6]));
	} catch {
		error.value = t("تعذر تحميل لوحة الجدولة.", "Couldn't load the schedule board.");
	} finally {
		loading.value = false;
	}
}
function move(days: number) {
	const next = new Date(cursor.value);
	next.setDate(next.getDate() + days);
	cursor.value = next;
	load();
}
function today() {
	cursor.value = new Date();
	load();
}
const filteredVisits = computed(() => {
	const needle = query.value.trim().toLowerCase();
	return (board.value?.visits || []).filter((row) => {
		const team = row.service_team || "";
		if (teamFilter.value && team !== teamFilter.value) return false;
		return (
			!needle ||
			[row.customer_name, row.service_type, row.service_job, row.primary_technician].some(
				(value) =>
					String(value || "")
						.toLowerCase()
						.includes(needle),
			)
		);
	});
});
function dayVisits(day: Date) {
	return filteredVisits.value.filter(
		(row) => String(row.scheduled_start || "").slice(0, 10) === iso(day),
	);
}
function dayMaintenance(day: Date) {
	return (board.value?.maintenance || []).filter(
		(row) => String(row.due_date).slice(0, 10) === iso(day),
	);
}
function time(value?: string) {
	if (!value) return "—";
	return new Intl.DateTimeFormat(lang.value === "ar" ? "ar-SA" : "en-GB", {
		hour: "2-digit",
		minute: "2-digit",
	}).format(new Date(value.replace(" ", "T")));
}
function dayLabel(day: Date) {
	return new Intl.DateTimeFormat(lang.value === "ar" ? "ar-SA" : "en-GB", {
		weekday: "short",
		day: "numeric",
		month: "short",
	}).format(day);
}

onMounted(load);
</script>

<template>
	<div class="space-y-6">
		<PageHeader
			:eyebrow="t('التخطيط والتوزيع', 'Planning and dispatch')"
			:title="t('لوحة الجدولة والتشغيل', 'Scheduling & operations board')"
			:subtitle="
				t(
					'الزيارات والصيانة والفرق والمركبات في صورة تشغيلية واحدة',
					'Visits, maintenance, teams and vehicles in one operational view',
				)
			"
		/>

		<div
			class="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-border bg-bg p-3 shadow-card"
		>
			<div class="flex items-center gap-2">
				<button class="rounded-lg border border-border px-3 py-2" @click="move(-7)">
					‹
				</button>
				<button
					class="rounded-lg border border-border px-3 py-2 text-sm font-semibold"
					@click="today"
				>
					{{ t("اليوم", "Today") }}
				</button>
				<button class="rounded-lg border border-border px-3 py-2" @click="move(7)">
					›
				</button>
				<strong class="px-2 text-sm"
					>{{ dayLabel(weekDays[0]) }} — {{ dayLabel(weekDays[6]) }}</strong
				>
			</div>
			<div class="flex rounded-xl bg-surface p-1">
				<button
					v-for="mode in ['calendar', 'agenda', 'resources'] as ViewMode[]"
					:key="mode"
					class="rounded-lg px-3 py-2 text-sm"
					:class="view === mode ? 'bg-primary text-white' : 'text-muted'"
					@click="view = mode"
				>
					{{
						mode === "calendar"
							? t("التقويم", "Calendar")
							: mode === "agenda"
								? t("الجدول", "Agenda")
								: t("الفرق والمركبات", "Teams & vehicles")
					}}
				</button>
			</div>
		</div>

		<div v-if="loading" class="flex justify-center p-16"><Spinner /></div>
		<p v-else-if="error" class="rounded-xl bg-danger/10 p-4 text-danger">{{ error }}</p>
		<template v-else-if="board">
			<section class="grid grid-cols-2 gap-3 lg:grid-cols-4">
				<div
					v-for="item in [
						[t('الزيارات', 'Visits'), board.summary.visits],
						[t('استحقاقات الصيانة', 'Maintenance due'), board.summary.maintenance_due],
						[t('الفرق النشطة', 'Active teams'), board.summary.active_teams],
						[t('غير المسند', 'Unassigned'), board.summary.unassigned],
					]"
					:key="String(item[0])"
					class="rounded-2xl border border-border bg-bg p-4 shadow-card"
				>
					<p class="text-xs text-muted">{{ item[0] }}</p>
					<p class="mt-1 text-2xl font-bold">{{ item[1] }}</p>
				</div>
			</section>

			<div v-if="view !== 'resources'" class="flex flex-wrap gap-3">
				<input
					v-model="query"
					class="min-w-64 rounded-xl border border-border bg-bg px-4 py-2 text-sm"
					:placeholder="
						t(
							'ابحث بالعميل أو المهمة أو الفني…',
							'Search customer, task or technician…',
						)
					"
				/>
				<select
					v-model="teamFilter"
					class="rounded-xl border border-border bg-bg px-4 py-2 text-sm"
				>
					<option value="">{{ t("كل الفرق", "All teams") }}</option>
					<option v-for="team in board.teams" :key="team.name" :value="team.name">
						{{ team.team_name }}
					</option>
				</select>
			</div>

			<section v-if="view === 'calendar'" class="grid gap-3 xl:grid-cols-7">
				<div
					v-for="day in weekDays"
					:key="iso(day)"
					class="min-h-56 rounded-2xl border border-border bg-bg p-3 shadow-card"
				>
					<div class="mb-3 flex items-center justify-between border-b border-border pb-2">
						<strong class="text-sm">{{ dayLabel(day) }}</strong
						><span class="rounded-full bg-surface px-2 text-xs">{{
							dayVisits(day).length + dayMaintenance(day).length
						}}</span>
					</div>
					<RouterLink
						v-for="row in dayVisits(day)"
						:key="row.name"
						:to="`/jobs/${row.service_job}`"
						class="mb-2 block rounded-xl border-s-4 border-primary bg-surface p-2.5 text-xs transition hover:shadow-card"
					>
						<div class="flex justify-between gap-2">
							<strong>{{ time(row.scheduled_start) }}</strong
							><StatusPill :status="row.status" />
						</div>
						<p class="mt-2 font-semibold">{{ row.customer_name || row.service_job }}</p>
						<p class="mt-1 text-muted">
							{{ row.service_type || t("زيارة خدمة", "Service visit") }}
						</p>
						<p class="mt-1 text-muted">
							{{
								row.service_team ||
								row.primary_technician ||
								t("غير مسند", "Unassigned")
							}}
						</p>
					</RouterLink>
					<RouterLink
						v-for="row in dayMaintenance(day)"
						:key="row.name"
						to="/maintenance"
						class="mb-2 block rounded-xl border-s-4 border-warning bg-warning/5 p-2.5 text-xs"
					>
						<strong>{{ t("صيانة دورية", "Preventive maintenance") }}</strong>
						<p class="mt-1">{{ row.customer }}</p>
						<p class="text-muted">
							{{ row.equipment_count }} {{ t("معدة", "equipment") }} ·
							{{ row.status }}
						</p>
					</RouterLink>
					<p
						v-if="!dayVisits(day).length && !dayMaintenance(day).length"
						class="py-8 text-center text-xs text-muted"
					>
						{{ t("لا توجد أعمال", "No work") }}
					</p>
				</div>
			</section>

			<section
				v-else-if="view === 'agenda'"
				class="overflow-x-auto rounded-2xl border border-border bg-bg shadow-card"
			>
				<table class="w-full text-sm">
					<thead>
						<tr class="border-b border-border text-muted">
							<th class="p-4">{{ t("الموعد", "Schedule") }}</th>
							<th class="p-4">{{ t("العميل والمهمة", "Customer & task") }}</th>
							<th class="p-4">{{ t("الفريق / الفني", "Team / technician") }}</th>
							<th class="p-4">{{ t("المعدات", "Equipment") }}</th>
							<th class="p-4">{{ t("الحالة", "Status") }}</th>
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="row in filteredVisits"
							:key="row.name"
							class="border-b border-border/60"
						>
							<td class="p-4">{{ formatDate(row.scheduled_start, true) }}</td>
							<td class="p-4">
								<RouterLink
									class="font-semibold text-primary"
									:to="`/jobs/${row.service_job}`"
									>{{ row.customer_name || row.service_job }}</RouterLink
								>
								<p class="text-xs text-muted">{{ row.service_type }}</p>
							</td>
							<td class="p-4">
								{{
									row.service_team ||
									row.primary_technician ||
									t("غير مسند", "Unassigned")
								}}
							</td>
							<td class="p-4">{{ row.equipment_count }}</td>
							<td class="p-4"><StatusPill :status="row.status" /></td>
						</tr>
					</tbody>
				</table>
			</section>

			<section v-else class="space-y-4">
				<div class="rounded-2xl border border-border bg-bg p-5 shadow-card">
					<h2 class="text-lg font-bold">
						{{
							t(
								"تقرير الفرق والمركبات والإسناد",
								"Teams, vehicles & assignment report",
							)
						}}
					</h2>
					<p class="mt-1 text-sm text-muted">
						{{
							t(
								"يعرض جاهزية كل فريق ومركبته ومستودعه وحمل الزيارات للأسبوع المحدد.",
								"Shows every team’s vehicle, warehouse and visit workload for the selected week.",
							)
						}}
					</p>
				</div>
				<div class="grid gap-4 lg:grid-cols-2">
					<article
						v-for="team in board.teams"
						:key="team.name"
						class="rounded-2xl border border-border bg-bg p-5 shadow-card"
					>
						<div class="flex items-start justify-between gap-3">
							<div>
								<h3 class="font-bold">{{ team.team_name }}</h3>
								<p class="text-sm text-muted">
									{{
										team.territory || t("النطاق غير محدد", "Territory not set")
									}}
								</p>
							</div>
							<span
								class="rounded-full bg-success/15 px-2.5 py-1 text-xs font-medium text-success"
								>{{ team.status }}</span
							>
						</div>
						<div class="mt-4 grid grid-cols-2 gap-3 text-sm">
							<div class="rounded-xl bg-surface p-3">
								<p class="text-xs text-muted">
									{{ t("المركبة / الفان", "Vehicle / van") }}
								</p>
								<strong>{{ team.vehicle || t("غير محددة", "Not set") }}</strong>
							</div>
							<div class="rounded-xl bg-surface p-3">
								<p class="text-xs text-muted">
									{{ t("زيارات الأسبوع", "Week visits") }}
								</p>
								<strong>{{ team.visit_count }} / {{ team.capacity || "—" }}</strong>
							</div>
							<div class="rounded-xl bg-surface p-3">
								<p class="text-xs text-muted">
									{{ t("قائد الفريق", "Team leader") }}
								</p>
								<strong>{{ team.team_leader || "—" }}</strong>
							</div>
							<div class="rounded-xl bg-surface p-3">
								<p class="text-xs text-muted">
									{{ t("مستودع المركبة", "Van warehouse") }}
								</p>
								<strong>{{ team.default_warehouse || "—" }}</strong>
							</div>
						</div>
						<div class="mt-4">
							<p class="text-xs font-semibold text-muted">
								{{ t("الأعضاء", "Members") }}
							</p>
							<div class="mt-2 flex flex-wrap gap-2">
								<span
									v-for="member in team.members"
									:key="member.technician"
									class="rounded-full border border-border px-3 py-1 text-xs"
									>{{ member.technician }} · {{ member.role_in_team }}</span
								><span v-if="!team.members.length" class="text-xs text-muted">{{
									t("لا يوجد أعضاء مسجلون", "No registered members")
								}}</span>
							</div>
						</div>
					</article>
				</div>
			</section>
		</template>
	</div>
</template>

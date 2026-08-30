<script setup lang="ts">
import { ref, reactive, computed, onMounted, onBeforeUnmount } from "vue";
import { RouterLink, useRouter } from "vue-router";
import { StatusPill, Spinner } from "@digit/ui";
import {
	getJob,
	startJobTask,
	completeJobTask,
	completeJob,
	createInvoiceFromJob,
	suggestTechnicians,
	assignTechnician,
	suggestTeams,
	assignTeam,
	getJobLogistics,
	requestParts,
	updateJob,
	estimateJob,
	getMessages,
	postMessage,
	getFeedback,
	listFieldNotes,
	addFieldNote,
	getJobVisits,
	createVisit,
	planServiceJob,
	scheduleServiceJob,
	dispatchServiceJob,
	getJobHub,
	type JobDoc,
	type TechnicianSuggestion,
	type TeamSuggestion,
	type JobLogistics,
	type JobEstimate,
	type JobMessage,
	type JobFeedback,
	type FieldNote,
	type ServiceVisitRow,
	type JobHub,
} from "@/lib/fsm";
import { realtime, JOB_MESSAGE_EVENT, type JobMessageEvent } from "@/lib/realtime";
import { t } from "@/lib/i18n";
import {
	translateActor,
	translateBlocker,
	translateNextAction,
	translateProcessAction,
} from "@/lib/translations";

const props = defineProps<{ name: string }>();
const router = useRouter();

const statusAr: Record<string, string> = {
	Draft: "مسودة",
	Planned: "مخطط",
	Scheduled: "مجدول",
	Dispatched: "موزع",
	"In Progress": "قيد التنفيذ",
	"On Hold": "معلق",
	Completed: "مكتمل",
	Cancelled: "ملغي",
	Pending: "قيد الانتظار",
	Submitted: "معتمد",
	Ordered: "تم الطلب",
	Received: "مستلم",
	Transferred: "منقول",
	"Partially Ordered": "مطلوب جزئياً",
	"Partially Received": "مستلم جزئياً",
	Stopped: "متوقف",
	"To Bill": "بانتظار الفوترة",
};
const showStatus = (s?: string) => (s ? t(statusAr[s] ?? s, s) : "—");

const phaseAr: Record<string, string> = {
	Planning: "التخطيط",
	Travel: "التنقل",
	"Check-In": "تسجيل الوصول",
	Inspection: "الفحص",
	Diagnosis: "التشخيص",
	"On-Site Service": "الخدمة الميدانية",
	Workshop: "الورشة",
	Testing: "الاختبار",
	"Customer Verification": "تحقق العميل",
	Closeout: "الإقفال",
};
const showPhase = (s?: string) => (s ? t(phaseAr[s] ?? s, s) : "—");

const priorityAr: Record<string, string> = {
	Low: "منخفضة",
	Medium: "متوسطة",
	High: "عالية",
	Urgent: "عاجلة",
};
const showPriority = (s?: string) => (s ? t(priorityAr[s] ?? s, s) : "—");

const showNextAction = (na?: { code?: string; message?: string; action?: string }) => {
	if (!na) return "";
	const en = na.message || na.action || na.code || "";
	return t(translateNextAction(na), en);
};
const showActor = (a?: string) => (a ? t(translateActor(a), a) : "");
const showBlocker = (blocker: JobHub["completion_blockers"][number]) =>
	t(translateBlocker(blocker), blocker.message);
const showProcessAction = (action?: string) =>
	action ? t(translateProcessAction(action), action) : "";

const roleAr: Record<string, string> = {
	Dispatcher: "المُرسل",
	Technician: "الفني",
	Customer: "العميل",
	System: "النظام",
};
const showRole = (s?: string) => (s ? t(roleAr[s] ?? s, s) : "—");

const mrTypeAr: Record<string, string> = {
	"Material Transfer": "نقل مواد",
	"Material Issue": "صرف مواد",
	Purchase: "شراء",
	Manufacture: "تصنيع",
};
const showMrType = (s?: string) => (s ? t(mrTypeAr[s] ?? s, s) : "—");

const job = ref<JobDoc | null>(null);
const loading = ref(true);
const error = ref("");
const busyTask = ref<number | null>(null);
const nextActionBusy = ref(false);
const completing = ref(false);
const invoicing = ref(false);
const note = ref("");
const visits = ref<ServiceVisitRow[]>([]);
const creatingVisit = ref(false);
const hub = ref<JobHub | null>(null);

function relatedRoute(type: string) {
	return `/jobs/${props.name}/related/${type}`;
}

function blockerRoute(blocker: JobHub["completion_blockers"][number]) {
	if (blocker.code === "ACTIVE_VISITS") return `/visits?job=${props.name}`;
	if (blocker.code === "INSPECTIONS_INCOMPLETE") return relatedRoute("inspections");
	if (blocker.code === "CRITICAL_FAILURES_OPEN") return relatedRoute("failures");
	if (blocker.code === "WORKSHOP_OPEN") return relatedRoute("workshop");
	if (["SERVICE_REPORT_REQUIRED", "SERVICE_REPORT_NOT_SUBMITTED"].includes(blocker.code))
		return relatedRoute("reports");
	if (blocker.code === "SERVICE_CERTIFICATE_REQUIRED") return relatedRoute("certificates");
	return blocker.route || `/jobs/${props.name}`;
}

const hubCards = computed(() => {
	if (!hub.value) return [];
	return [
		{
			key: "visits",
			label: t("الزيارات", "Visits"),
			value: hub.value.visits.length,
			to: `/visits?job=${props.name}`,
		},
		{
			key: "inspections",
			label: t("الفحوصات", "Inspections"),
			value: hub.value.inspections.length,
			to: relatedRoute("inspections"),
		},
		{
			key: "failures",
			label: t("الأعطال", "Failures"),
			value: hub.value.failures.length,
			to: relatedRoute("failures"),
		},
		{
			key: "workshop",
			label: t("الورشة", "Workshop"),
			value: hub.value.workshop.length,
			to: relatedRoute("workshop"),
		},
		{
			key: "reports",
			label: t("التقارير", "Reports"),
			value: hub.value.reports.length,
			to: relatedRoute("reports"),
		},
		{
			key: "certificates",
			label: t("الشهادات", "Certificates"),
			value: hub.value.certificates.length,
			to: relatedRoute("certificates"),
		},
	];
});

async function loadVisits() {
	try {
		visits.value = await getJobVisits(props.name);
	} catch {
		visits.value = [];
	}
}

async function addVisit() {
	creatingVisit.value = true;
	error.value = "";
	try {
		await createVisit(props.name);
		await Promise.all([loadVisits(), refreshHub()]);
	} catch {
		error.value = t(
			"تعذّر إنشاء الزيارة. يجب أن يكون أمر الخدمة مخططًا ونشطًا.",
			"Couldn't create the visit. The service job must be planned and active.",
		);
	} finally {
		creatingVisit.value = false;
	}
}

async function refreshHub() {
	try {
		hub.value = await getJobHub(props.name);
	} catch {
		hub.value = null;
	}
}

const suggestions = ref<TechnicianSuggestion[]>([]);
const loadingSuggestions = ref(false);
const assigningTo = ref<string | null>(null);
const assignError = ref("");

async function loadSuggestions() {
	if (!job.value) return;
	loadingSuggestions.value = true;
	assignError.value = "";
	try {
		suggestions.value = await suggestTechnicians(job.value.name);
	} catch {
		assignError.value = t(
			"تعذّر تحميل اقتراحات الفنيين.",
			"Couldn't load technician suggestions.",
		);
	} finally {
		loadingSuggestions.value = false;
	}
}

async function assign(technician: string) {
	if (!job.value) return;
	assigningTo.value = technician;
	assignError.value = "";
	try {
		job.value = await assignTechnician(job.value.name, technician);
		suggestions.value = [];
		await refreshHub();
	} catch (e) {
		assignError.value =
			(e as { message?: string })?.message ||
			t("تعذّر إسناد هذا الفني.", "Couldn't assign this technician.");
	} finally {
		assigningTo.value = null;
	}
}

const teamSuggestions = ref<TeamSuggestion[]>([]);
const loadingTeamSuggestions = ref(false);
const assigningTeamTo = ref<string | null>(null);
const teamAssignError = ref("");

async function loadTeamSuggestions() {
	if (!job.value) return;
	loadingTeamSuggestions.value = true;
	teamAssignError.value = "";
	try {
		teamSuggestions.value = await suggestTeams(job.value.name);
	} catch {
		teamAssignError.value = t("تعذّر تحميل اقتراحات الفرق.", "Couldn't load team suggestions.");
	} finally {
		loadingTeamSuggestions.value = false;
	}
}

async function assignTeamTo(team: string) {
	if (!job.value) return;
	assigningTeamTo.value = team;
	teamAssignError.value = "";
	try {
		job.value = await assignTeam(job.value.name, team);
		teamSuggestions.value = [];
		await refreshHub();
	} catch (e) {
		teamAssignError.value =
			(e as { message?: string })?.message ||
			t("تعذّر إسناد هذا الفريق.", "Couldn't assign this team.");
	} finally {
		assigningTeamTo.value = null;
	}
}

const tasks = computed(() => [...(job.value?.tasks ?? [])].sort((a, b) => a.idx - b.idx));
const doneCount = computed(() => tasks.value.filter((t) => t.status === "Done").length);
const activeIdx = computed(() => tasks.value.find((t) => t.status !== "Done")?.idx ?? null);
const allDone = computed(() => tasks.value.length > 0 && activeIdx.value === null);

const currency = (n?: number) =>
	new Intl.NumberFormat(undefined, { style: "currency", currency: "USD" }).format(n ?? 0);

const datetime = (iso?: string) =>
	iso
		? new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })
		: "—";

const time = (iso?: string) =>
	iso ? new Date(iso).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" }) : "";

const logistics = ref<JobLogistics | null>(null);
const requesting = ref(false);

async function loadLogistics() {
	try {
		logistics.value = await getJobLogistics(props.name);
	} catch {
		logistics.value = null;
	}
}

async function requestJobParts() {
	if (!job.value?.items?.length) return;
	requesting.value = true;
	error.value = "";
	try {
		const items = job.value.items.map((i) => ({ item_code: i.item_code, qty: i.qty }));
		await requestParts(job.value.name, items);
		await loadLogistics();
	} catch (e) {
		error.value =
			(e as { message?: string })?.message ||
			t(
				"تعذّر طلب القطع. حدد مستودع المركبة أو المستودع الافتراضي أولاً.",
				"Couldn't request parts. Set a van/default warehouse first.",
			);
	} finally {
		requesting.value = false;
	}
}

const costForm = reactive({ labor_rate: 0, overhead_cost: 0, estimated_hours: 0 });
const savingCost = ref(false);
const estimate = ref<JobEstimate | null>(null);
const estimating = ref(false);

function syncCostForm() {
	costForm.labor_rate = job.value?.labor_rate ?? 0;
	costForm.overhead_cost = job.value?.overhead_cost ?? 0;
	costForm.estimated_hours = job.value?.estimated_hours ?? 0;
}

async function saveCosts() {
	if (!job.value) return;
	savingCost.value = true;
	error.value = "";
	try {
		job.value = await updateJob(job.value.name, {
			labor_rate: costForm.labor_rate,
			overhead_cost: costForm.overhead_cost,
			estimated_hours: costForm.estimated_hours,
		});
		syncCostForm();
	} catch {
		error.value = t("تعذّر حفظ التكاليف.", "Couldn't save costing.");
	} finally {
		savingCost.value = false;
	}
}

async function runEstimate() {
	if (!job.value?.service_type) return;
	estimating.value = true;
	try {
		estimate.value = await estimateJob(job.value.service_type, job.value.primary_technician);
	} catch {
		estimate.value = null;
	} finally {
		estimating.value = false;
	}
}

function useEstimate() {
	if (estimate.value?.avg_hours != null) costForm.estimated_hours = estimate.value.avg_hours;
}

const messages = ref<JobMessage[]>([]);
const newMessage = ref("");
const postingMsg = ref(false);
let offMessage: (() => void) | null = null;

async function loadMessages() {
	try {
		messages.value = await getMessages(props.name);
	} catch {
		messages.value = [];
	}
}

async function sendMessage() {
	const text = newMessage.value.trim();
	if (!text) return;
	postingMsg.value = true;
	try {
		await postMessage(props.name, text);
		newMessage.value = "";
		await loadMessages();
	} catch {
		error.value = t("تعذّر إرسال الرسالة.", "Couldn't send the message.");
	} finally {
		postingMsg.value = false;
	}
}

const feedback = ref<JobFeedback | null>(null);
async function loadFeedback() {
	try {
		feedback.value = await getFeedback(props.name);
	} catch {
		feedback.value = null;
	}
}

const fieldNotes = ref<FieldNote[]>([]);
const newNote = ref("");
const savingNote = ref(false);

async function loadFieldNotes() {
	if (!job.value?.customer) return;
	try {
		fieldNotes.value = await listFieldNotes(job.value.customer);
	} catch {
		fieldNotes.value = [];
	}
}

async function saveFieldNote() {
	const text = newNote.value.trim();
	if (!text || !job.value?.customer) return;
	savingNote.value = true;
	try {
		await addFieldNote(job.value.customer, text, job.value.name);
		newNote.value = "";
		await loadFieldNotes();
	} catch {
		error.value = t("تعذّر حفظ الملاحظة.", "Couldn't save the note.");
	} finally {
		savingNote.value = false;
	}
}

async function load() {
	loading.value = true;
	error.value = "";
	try {
		job.value = await getJob(props.name);
		await refreshHub();
		syncCostForm();
		loadLogistics();
		loadMessages();
		loadFeedback();
		loadFieldNotes();
		loadVisits();
	} catch {
		error.value = t("تعذّر تحميل أمر الخدمة.", "Couldn't load this job.");
	} finally {
		loading.value = false;
	}
}

async function runNextAction() {
	if (!job.value || !hub.value) return;
	const action = hub.value.next_action;
	if (!action) return;
	const blocker = hub.value.completion_blockers[0];
	if (blocker && action.code === blocker.code) {
		await router.push(blockerRoute(blocker));
		return;
	}
	if (action.route) {
		await router.push(action.route);
		return;
	}
	nextActionBusy.value = true;
	error.value = "";
	try {
		if (action.code === "PLAN_JOB") {
			job.value = await planServiceJob(job.value.name);
		} else if (action.code === "SCHEDULE_JOB") {
			if (!job.value.scheduled_date) {
				error.value = t(
					"حدد تاريخ ووقت الجدولة في أمر الخدمة أولًا.",
					"Set the service job schedule date and time first.",
				);
				return;
			}
			job.value = await scheduleServiceJob(
				job.value.name,
				job.value.scheduled_date,
				job.value.scheduled_end,
			);
		} else if (action.code === "DISPATCH_JOB") {
			if (!job.value.primary_technician) {
				error.value = t(
					"أسند فنيًا رئيسيًا قبل توزيع أمر الخدمة.",
					"Assign a primary technician before dispatching the service job.",
				);
				return;
			}
			job.value = await dispatchServiceJob(job.value.name);
		} else if (action.code === "COMPLETE_JOB") {
			await finishJob();
			return;
		} else {
			error.value = t(
				"استخدم القسم المرتبط أدناه لتنفيذ هذا الإجراء.",
				"Use the related section below to perform this action.",
			);
			return;
		}
		await refreshHub();
	} catch {
		error.value = t("تعذّر تنفيذ الإجراء التالي.", "Couldn't perform the next action.");
	} finally {
		nextActionBusy.value = false;
	}
}

async function start(idx: number) {
	if (!job.value) return;
	busyTask.value = idx;
	error.value = "";
	try {
		job.value = await startJobTask(job.value.name, idx);
	} catch {
		error.value = t("تعذّر بدء هذه الخطوة.", "Couldn't start this step.");
	} finally {
		busyTask.value = null;
	}
}

async function complete(idx: number) {
	if (!job.value) return;
	busyTask.value = idx;
	error.value = "";
	try {
		job.value = await completeJobTask(job.value.name, idx, note.value || undefined);
		note.value = "";
	} catch {
		error.value = t("تعذّر إتمام هذه الخطوة.", "Couldn't complete this step.");
	} finally {
		busyTask.value = null;
	}
}

async function finishJob() {
	if (!job.value) return;
	const blocker = hub.value?.completion_blockers[0];
	if (blocker) {
		error.value = t(
			"أكمل المتطلب الموضح قبل إغلاق أمر الخدمة.",
			"Complete the displayed requirement before closing the service job.",
		);
		await router.push(blockerRoute(blocker));
		return;
	}
	completing.value = true;
	error.value = "";
	try {
		job.value = await completeJob(job.value.name);
		await refreshHub();
	} catch {
		error.value = t("تعذّر إتمام أمر الخدمة.", "Couldn't complete the job.");
	} finally {
		completing.value = false;
	}
}

async function generateInvoice() {
	if (!job.value) return;
	invoicing.value = true;
	error.value = "";
	try {
		const res = await createInvoiceFromJob(job.value.name);
		job.value = { ...job.value, sales_invoice: res.name };
	} catch {
		error.value = t(
			"تعذّر إنشاء الفاتورة. تأكد من وجود بنود في أمر الخدمة وشركة افتراضية.",
			"Couldn't create the invoice. Ensure the job has items and a default company.",
		);
	} finally {
		invoicing.value = false;
	}
}

onMounted(() => {
	load();
	try {
		offMessage = realtime().on(JOB_MESSAGE_EVENT, (m: JobMessageEvent) => {
			if (m.service_job === props.name) loadMessages();
		});
	} catch {
		offMessage = null;
	}
});

onBeforeUnmount(() => offMessage?.());
</script>

<template>
	<div>
		<RouterLink
			to="/dispatch"
			class="mb-4 inline-flex items-center gap-1 text-sm text-fg-muted hover:text-fg"
		>
			← {{ t("العودة إلى لوحة التوزيع", "Back to dispatch") }}
		</RouterLink>

		<div v-if="loading" class="flex justify-center py-16"><Spinner :size="28" /></div>
		<div
			v-else-if="error && !job"
			class="rounded-2xl border border-danger/30 bg-danger/10 p-4 text-sm text-danger"
		>
			{{ error }}
		</div>

		<div v-else-if="job" class="space-y-6">
			<div class="flex flex-wrap items-start justify-between gap-3">
				<div>
					<div class="flex flex-wrap items-center gap-3">
						<RouterLink
							:to="`/customers/${job.customer}`"
							class="text-2xl font-bold text-fg hover:text-primary"
						>
							{{ job.customer_name || job.customer }}
						</RouterLink>
						<StatusPill :status="job.status" />
					</div>
					<p class="mt-0.5 font-mono text-sm text-fg-muted">{{ job.name }}</p>
				</div>
			</div>

			<section
				v-if="hub?.next_action"
				class="rounded-2xl border border-border bg-bg p-5 shadow-card"
			>
				<div class="flex flex-wrap items-start justify-between gap-4">
					<div>
						<p class="text-xs uppercase tracking-wide text-fg-muted">
							{{ t("الإجراء التالي", "Next Action") }}
						</p>
						<button
							type="button"
							:disabled="nextActionBusy"
							class="mt-1 text-start text-lg font-semibold text-primary hover:underline disabled:opacity-60"
							@click="runNextAction"
						>
							<Spinner v-if="nextActionBusy" class="me-2 inline-block" :size="16" />
							{{ showNextAction(hub.next_action) }}
						</button>
						<p class="mt-1 text-xs text-fg-muted">
							{{ showActor(hub.next_action.responsible_actor) }}
						</p>
					</div>
					<div class="text-sm text-fg-muted">
						<span v-if="job.project"
							>{{ t("المشروع", "Project") }}: {{ job.project }} · </span
						><span>{{ t("المرحلة", "Phase") }}: {{ showPhase(job.phase) }}</span>
					</div>
				</div>
				<div v-if="hub.completion_blockers.length" class="mt-4 grid gap-2 md:grid-cols-2">
					<RouterLink
						v-for="blocker in hub.completion_blockers"
						:key="blocker.code"
						:to="blockerRoute(blocker)"
						class="rounded-xl border border-warning/30 bg-warning/10 p-3"
						><p class="font-medium">{{ showBlocker(blocker) }}</p>
						<p class="mt-1 text-xs text-fg-muted">
							{{ showProcessAction(blocker.action) }} ·
							{{ showActor(blocker.responsible_actor) }}
						</p></RouterLink
					>
				</div>
				<div class="mt-4 grid grid-cols-3 gap-2 text-center text-xs sm:grid-cols-6">
					<RouterLink
						v-for="item in hubCards"
						:key="item.key"
						:to="item.to"
						class="rounded-xl bg-white/3 p-3 transition hover:bg-white/8 hover:text-primary"
					>
						<p class="text-lg font-bold">{{ item.value }}</p>
						<p class="text-fg-muted">{{ item.label }}</p>
					</RouterLink>
				</div>
			</section>

			<div class="grid grid-cols-1 gap-6 lg:grid-cols-3">
				<div class="space-y-6 lg:col-span-2">
					<section class="rounded-2xl border border-border bg-bg p-4 shadow-card">
						<div class="flex items-center justify-between">
							<h2 class="text-lg font-bold">
								{{ t("زيارات الخدمة", "Service Visits") }}
							</h2>
							<button
								type="button"
								class="rounded-lg border border-border px-3 py-1.5 text-sm"
								:disabled="
									creatingVisit ||
									['Draft', 'Completed', 'Cancelled'].includes(job.status)
								"
								@click="addVisit"
							>
								{{ t("إنشاء زيارة", "Create visit") }}
							</button>
						</div>
						<div class="mt-3 space-y-2">
							<RouterLink
								v-for="visit in visits"
								:key="visit.name"
								:to="`/visits?job=${job.name}`"
								class="flex items-center justify-between rounded-xl bg-white/3 p-3"
							>
								<div>
									<p class="font-medium">
										{{
											t(
												`الزيارة ${visit.visit_number}`,
												`Visit ${visit.visit_number}`,
											)
										}}
									</p>
									<p class="text-xs text-fg-muted">
										{{ visit.name }} · {{ datetime(visit.scheduled_start) }}
									</p>
								</div>
								<StatusPill :status="visit.status" />
							</RouterLink>
							<p v-if="!visits.length" class="text-sm text-fg-muted">
								{{ t("لا توجد زيارات بعد.", "No service visits yet.") }}
							</p>
						</div>
					</section>
					<section
						class="rounded-2xl border border-border bg-bg shadow-card backdrop-blur-xl"
					>
						<div
							class="flex items-center justify-between border-b border-border px-4 py-3"
						>
							<h2 class="text-lg font-bold">{{ t("قائمة المهام", "Checklist") }}</h2>
							<span
								v-if="tasks.length"
								class="rounded-full bg-white/5 px-2.5 py-0.5 font-mono text-xs text-fg-muted tabular-nums"
							>
								{{ doneCount }}/{{ tasks.length }}
							</span>
						</div>

						<ul v-if="tasks.length" class="divide-y divide-border">
							<li
								v-for="task in tasks"
								:key="task.idx"
								class="flex items-start gap-3 px-4 py-3"
								:class="{
									'opacity-50': task.status !== 'Done' && task.idx !== activeIdx,
								}"
							>
								<span
									class="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full border"
									:class="
										task.status === 'Done'
											? 'border-brand bg-brand text-white'
											: task.idx === activeIdx
												? 'border-brand text-brand'
												: 'border-border text-fg-muted'
									"
								>
									<svg
										v-if="task.status === 'Done'"
										viewBox="0 0 24 24"
										class="size-3.5"
										fill="none"
										stroke="currentColor"
										stroke-width="3"
										stroke-linecap="round"
										stroke-linejoin="round"
										aria-hidden="true"
									>
										<path d="M20 6 9 17l-5-5" />
									</svg>
									<span v-else class="font-mono text-xs">{{ task.idx }}</span>
								</span>

								<div class="min-w-0 flex-1">
									<p
										class="text-base"
										:class="{
											'text-fg-muted line-through': task.status === 'Done',
										}"
									>
										{{ task.task }}
									</p>
									<p
										v-if="task.note"
										class="text-sm text-fg-muted"
										:class="{ 'line-through': task.status === 'Done' }"
									>
										{{ task.note }}
									</p>
									<p
										v-if="task.status === 'Done' && task.completed_on"
										class="mt-0.5 text-xs text-fg-muted"
									>
										{{ t("أُنجزت في", "Done at") }}
										{{ time(task.completed_on) }}
									</p>

									<div v-if="task.idx === activeIdx" class="mt-2">
										<button
											v-if="task.status === 'Pending'"
											type="button"
											:disabled="busyTask === task.idx"
											class="kl-grad-brand inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-semibold text-white shadow-e2 transition-[filter] hover:brightness-110 disabled:opacity-60"
											@click="start(task.idx)"
										>
											<Spinner v-if="busyTask === task.idx" :size="14" />
											{{ t("بدء الخطوة", "Start step") }}
										</button>
										<div v-else class="space-y-2">
											<input
												v-model="note"
												:placeholder="
													t(
														'أضف ملاحظة (اختياري)',
														'Add a note (optional)',
													)
												"
												class="w-full rounded-lg border border-border bg-white/5 px-3 py-1.5 text-sm focus-visible:outline-none focus-visible:[box-shadow:var(--kl-elevation-focus)]"
											/>
											<button
												type="button"
												:disabled="busyTask === task.idx"
												class="kl-grad-brand inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-semibold text-white shadow-e2 transition-[filter] hover:brightness-110 disabled:opacity-60"
												@click="complete(task.idx)"
											>
												<Spinner v-if="busyTask === task.idx" :size="14" />
												{{ t("إتمام الخطوة", "Complete step") }}
											</button>
										</div>
									</div>
									<p
										v-else-if="task.status !== 'Done'"
										class="mt-1 inline-flex items-center gap-1 text-xs text-fg-muted"
									>
										<svg
											viewBox="0 0 24 24"
											class="size-3.5"
											fill="none"
											stroke="currentColor"
											stroke-width="1.8"
											aria-hidden="true"
										>
											<rect x="5" y="11" width="14" height="9" rx="2" />
											<path d="M8 11V8a4 4 0 0 1 8 0v3" />
										</svg>
										{{ t("مقفلة", "Locked") }}
									</p>
								</div>
							</li>
						</ul>

						<div v-else class="px-4 py-6">
							<p class="text-sm text-fg-muted">
								{{
									t(
										"لا توجد قائمة مهام لهذا الأمر. حدده كمكتمل عند انتهاء العمل.",
										"No checklist on this job. Mark it complete when the work is done.",
									)
								}}
							</p>
							<button
								v-if="job.status !== 'Completed'"
								type="button"
								:disabled="completing"
								class="kl-grad-brand mt-3 inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-semibold text-white shadow-e2 transition-[filter] hover:brightness-110 disabled:opacity-60"
								@click="finishJob"
							>
								<Spinner v-if="completing" :size="14" />
								{{ t("إكمال أمر الخدمة", "Complete service job") }}
							</button>
						</div>

						<p
							v-if="allDone"
							class="border-t border-border px-4 py-3 text-sm font-medium text-success"
						>
							{{
								t(
									"اكتملت جميع الخطوات — تم تحديد أمر الخدمة كمكتمل.",
									"All steps complete — job marked completed.",
								)
							}}
						</p>
					</section>

					<section
						class="rounded-2xl border border-border bg-bg shadow-card backdrop-blur-xl"
					>
						<h2 class="border-b border-border px-4 py-3 text-lg font-bold">
							{{ t("قطع الغيار والخدمات", "Parts & services") }}
						</h2>
						<div class="overflow-x-auto">
							<table
								v-if="job.items?.length"
								class="w-full min-w-md text-left text-sm"
							>
								<thead class="border-b border-border text-fg-muted">
									<tr>
										<th class="px-4 py-2 font-medium">
											{{ t("الصنف", "Item") }}
										</th>
										<th class="px-4 py-2 text-right font-medium">
											{{ t("الكمية", "Qty") }}
										</th>
										<th class="px-4 py-2 text-right font-medium">
											{{ t("السعر", "Rate") }}
										</th>
										<th class="px-4 py-2 text-right font-medium">
											{{ t("المبلغ", "Amount") }}
										</th>
									</tr>
								</thead>
								<tbody>
									<tr
										v-for="(it, i) in job.items"
										:key="i"
										class="border-b border-border last:border-0"
									>
										<td class="px-4 py-2">
											{{ it.item_name || it.item_code }}
										</td>
										<td class="px-4 py-2 text-right font-mono tabular-nums">
											{{ it.qty }}
										</td>
										<td class="px-4 py-2 text-right font-mono tabular-nums">
											{{ currency(it.rate) }}
										</td>
										<td class="px-4 py-2 text-right font-mono tabular-nums">
											{{ currency(it.amount) }}
										</td>
									</tr>
								</tbody>
								<tfoot>
									<tr class="border-t border-border">
										<td class="px-4 py-2 font-medium" colspan="3">
											{{ t("الإجمالي", "Total") }}
										</td>
										<td
											class="px-4 py-2 text-right font-mono font-medium tabular-nums"
										>
											{{ currency(job.total_amount) }}
										</td>
									</tr>
								</tfoot>
							</table>
						</div>
						<p v-if="!job.items?.length" class="px-4 py-6 text-sm text-fg-muted">
							{{ t("لم تتم إضافة بنود.", "No items added.") }}
						</p>
					</section>
					<section
						class="rounded-2xl border border-border bg-bg shadow-card backdrop-blur-xl"
					>
						<div
							class="flex items-center justify-between border-b border-border px-4 py-3"
						>
							<h2 class="text-lg font-bold">
								{{ t("القطع والخدمات اللوجستية", "Parts & logistics") }}
							</h2>
							<button
								type="button"
								:disabled="requesting || !job.items?.length"
								class="inline-flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-1.5 text-sm font-medium text-fg hover:bg-bg-subtle disabled:opacity-50"
								@click="requestJobParts"
							>
								<Spinner v-if="requesting" :size="14" />
								{{ t("طلب قطع", "Request parts") }}
							</button>
						</div>

						<div
							v-if="
								logistics &&
								(logistics.material_requests.length ||
									logistics.delivery_notes.length)
							"
							class="divide-y divide-border"
						>
							<div
								v-for="mr in logistics.material_requests"
								:key="mr.name"
								class="flex items-center justify-between px-4 py-2.5 text-sm"
							>
								<div>
									<p class="font-mono text-xs text-fg">{{ mr.name }}</p>
									<p class="text-xs text-fg-muted">
										{{ showMrType(mr.material_request_type) }} ·
										{{ t("طُلب", "ordered") }}
										{{ Math.round(mr.per_ordered) }}% ·
										{{ t("استُلم", "received") }}
										{{ Math.round(mr.per_received) }}%
									</p>
								</div>
								<span
									class="rounded-full bg-white/5 px-2.5 py-0.5 text-xs text-fg-muted"
								>
									{{ showStatus(mr.status) }}
								</span>
							</div>
							<div
								v-for="dn in logistics.delivery_notes"
								:key="dn.name"
								class="flex items-center justify-between px-4 py-2.5 text-sm"
							>
								<div>
									<p class="font-mono text-xs text-fg">{{ dn.name }}</p>
									<p class="text-xs text-fg-muted">
										{{ t("توصيل", "Delivery") }} · {{ dn.posting_date }}
									</p>
								</div>
								<span
									class="rounded-full bg-white/5 px-2.5 py-0.5 text-xs text-fg-muted"
								>
									{{ showStatus(dn.status) }}
								</span>
							</div>
						</div>
						<p v-else class="px-4 py-6 text-sm text-fg-muted">
							{{
								t(
									"لا توجد طلبات قطع بعد. استخدم «طلب قطع» لنقل بنود هذا الأمر إلى مركبة الفني.",
									"No parts requests yet. Use “Request parts” to transfer this job's items to the technician's van.",
								)
							}}
						</p>
					</section>

					<section
						class="rounded-2xl border border-border bg-bg shadow-card backdrop-blur-xl"
					>
						<h2 class="border-b border-border px-4 py-3 text-lg font-bold">
							{{ t("التكاليف", "Costing") }}
						</h2>
						<div class="grid grid-cols-2 gap-px bg-border sm:grid-cols-4">
							<div class="bg-bg px-4 py-3">
								<p class="text-xs text-fg-muted">
									{{ t("الساعات الفعلية", "Actual hours") }}
								</p>
								<p class="font-mono text-lg tabular-nums text-fg">
									{{ (job.actual_hours ?? 0).toFixed(2) }}
								</p>
							</div>
							<div class="bg-bg px-4 py-3">
								<p class="text-xs text-fg-muted">{{ t("العمالة", "Labour") }}</p>
								<p class="font-mono text-lg tabular-nums text-fg">
									{{ currency(job.labor_cost) }}
								</p>
							</div>
							<div class="bg-bg px-4 py-3">
								<p class="text-xs text-fg-muted">{{ t("المواد", "Materials") }}</p>
								<p class="font-mono text-lg tabular-nums text-fg">
									{{ currency(job.materials_cost) }}
								</p>
							</div>
							<div class="bg-bg px-4 py-3">
								<p class="text-xs text-fg-muted">
									{{ t("إجمالي التكلفة", "Total cost") }}
								</p>
								<p class="font-mono text-lg font-semibold tabular-nums text-brand">
									{{ currency(job.total_cost) }}
								</p>
							</div>
						</div>

						<div class="space-y-3 border-t border-border p-4">
							<div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
								<label class="block">
									<span class="mb-1 block text-xs text-fg-muted">{{
										t("أجر الساعة", "Labour rate /hr")
									}}</span>
									<input
										v-model.number="costForm.labor_rate"
										type="number"
										min="0"
										class="w-full rounded-md border border-border bg-bg px-3 py-1.5 text-sm"
									/>
								</label>
								<label class="block">
									<span class="mb-1 block text-xs text-fg-muted">{{
										t("التكاليف غير المباشرة", "Overhead")
									}}</span>
									<input
										v-model.number="costForm.overhead_cost"
										type="number"
										min="0"
										class="w-full rounded-md border border-border bg-bg px-3 py-1.5 text-sm"
									/>
								</label>
								<label class="block">
									<span class="mb-1 block text-xs text-fg-muted">{{
										t("الساعات المقدّرة", "Estimated hours")
									}}</span>
									<input
										v-model.number="costForm.estimated_hours"
										type="number"
										min="0"
										class="w-full rounded-md border border-border bg-bg px-3 py-1.5 text-sm"
									/>
								</label>
							</div>

							<div class="flex flex-wrap items-center gap-3">
								<button
									type="button"
									:disabled="savingCost"
									class="kl-grad-brand inline-flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-sm font-semibold text-white shadow-e2 hover:brightness-110 disabled:opacity-60"
									@click="saveCosts"
								>
									<Spinner v-if="savingCost" :size="14" />
									{{ t("حفظ التكاليف", "Save costing") }}
								</button>
								<button
									v-if="job.service_type"
									type="button"
									:disabled="estimating"
									class="inline-flex items-center gap-2 rounded-lg border border-border bg-surface px-3.5 py-1.5 text-sm font-medium text-fg hover:bg-bg-subtle disabled:opacity-60"
									@click="runEstimate"
								>
									<Spinner v-if="estimating" :size="14" />
									{{ t("تقدير من السجل", "Estimate from history") }}
								</button>
								<p v-if="estimate" class="text-sm text-fg-muted">
									<template v-if="estimate.avg_hours != null">
										{{
											t(
												`~${estimate.avg_hours} ساعة وسطياً عبر ${estimate.sample_size} أمر (${estimate.basis})`,
												`~${estimate.avg_hours}h avg over ${estimate.sample_size} ${estimate.basis} job(s)`,
											)
										}}
										<button
											type="button"
											class="ml-1 font-medium text-brand hover:underline"
											@click="useEstimate"
										>
											{{ t("استخدام", "Use") }}
										</button>
									</template>
									<template v-else>{{
										t(
											`لا يوجد سجل بعد لـ «${estimate.service_type}».`,
											`No history yet for “${estimate.service_type}”.`,
										)
									}}</template>
								</p>
							</div>
						</div>
					</section>
					<section
						class="rounded-2xl border border-border bg-bg shadow-card backdrop-blur-xl"
					>
						<h2 class="border-b border-border px-4 py-3 text-lg font-bold">
							{{ t("الرسائل", "Messages") }}
						</h2>
						<div class="max-h-80 space-y-3 overflow-y-auto px-4 py-3">
							<p v-if="messages.length === 0" class="text-sm text-fg-muted">
								{{
									t(
										"لا توجد رسائل بعد. تواصل مع العميل أو الفني من هنا.",
										"No messages yet. Reach the customer or technician here.",
									)
								}}
							</p>
							<div v-for="m in messages" :key="m.name" class="text-sm">
								<div class="flex items-center gap-2">
									<span
										class="rounded-full px-2 py-0.5 text-xs font-medium"
										:class="{
											'bg-brand/15 text-brand':
												m.author_role === 'Dispatcher',
											'bg-info/15 text-info': m.author_role === 'Technician',
											'bg-success/15 text-success':
												m.author_role === 'Customer',
											'bg-fg-muted/15 text-fg-muted':
												m.author_role === 'System',
										}"
									>
										{{ showRole(m.author_role) }}
									</span>
									<span class="text-xs text-fg-muted">
										{{ m.author_name }} · {{ datetime(m.creation) }}
									</span>
								</div>
								<p class="mt-1 whitespace-pre-line text-fg">{{ m.message }}</p>
							</div>
						</div>
						<div class="flex gap-2 border-t border-border p-3">
							<input
								v-model="newMessage"
								:placeholder="t('اكتب رسالة…', 'Write a message…')"
								class="flex-1 rounded-lg border border-border bg-white/5 px-3 py-2 text-sm focus-visible:outline-none focus-visible:[box-shadow:var(--kl-elevation-focus)]"
								@keydown.enter="sendMessage"
							/>
							<button
								type="button"
								:disabled="postingMsg || !newMessage.trim()"
								class="kl-grad-brand inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold text-white shadow-e2 hover:brightness-110 disabled:opacity-50"
								@click="sendMessage"
							>
								<Spinner v-if="postingMsg" :size="14" />
								{{ t("إرسال", "Send") }}
							</button>
						</div>
					</section>
					<section
						class="rounded-2xl border border-border bg-bg shadow-card backdrop-blur-xl"
					>
						<h2 class="border-b border-border px-4 py-3 text-lg font-bold">
							{{ t("ملاحظات ميدانية عن العميل", "Customer field notes") }}
						</h2>
						<ul v-if="fieldNotes.length" class="divide-y divide-border">
							<li v-for="n in fieldNotes" :key="n.name" class="px-4 py-2.5 text-sm">
								<p class="whitespace-pre-line text-fg">{{ n.note }}</p>
								<p class="mt-0.5 text-xs text-fg-muted">
									{{ n.technician || "—" }} · {{ n.visit_date }}
									<span v-if="n.service_job === job.name" class="text-brand"
										>· {{ t("هذا الأمر", "this job") }}</span
									>
								</p>
							</li>
						</ul>
						<p v-else class="px-4 py-3 text-sm text-fg-muted">
							{{
								t(
									"لا توجد ملاحظات ميدانية لهذا العميل.",
									"No field notes for this customer.",
								)
							}}
						</p>
						<div class="flex gap-2 border-t border-border p-3">
							<input
								v-model="newNote"
								:placeholder="
									t(
										'أضف ملاحظة ميدانية (مثل رمز الدخول أو خصوصية المعدة)…',
										'Add a field note (e.g. access code, equipment quirk)…',
									)
								"
								class="flex-1 rounded-lg border border-border bg-white/5 px-3 py-2 text-sm focus-visible:outline-none focus-visible:[box-shadow:var(--kl-elevation-focus)]"
								@keydown.enter="saveFieldNote"
							/>
							<button
								type="button"
								:disabled="savingNote || !newNote.trim()"
								class="inline-flex items-center gap-2 rounded-lg border border-border bg-surface px-4 py-2 text-sm font-medium text-fg hover:bg-bg-subtle disabled:opacity-50"
								@click="saveFieldNote"
							>
								<Spinner v-if="savingNote" :size="14" />
								{{ t("إضافة", "Add") }}
							</button>
						</div>
					</section>

					<section
						v-if="job.notes"
						class="rounded-2xl border border-border bg-bg p-4 shadow-card backdrop-blur-xl"
					>
						<h2 class="mb-2 text-lg font-bold">{{ t("الملاحظات", "Notes") }}</h2>
						<p class="whitespace-pre-line text-sm text-fg">{{ job.notes }}</p>
					</section>
				</div>

				<aside
					class="space-y-3 rounded-2xl border border-border bg-bg p-4 shadow-card backdrop-blur-xl"
				>
					<dl class="space-y-3 text-sm">
						<div>
							<dt class="text-fg-muted">{{ t("الموعد المجدول", "Scheduled") }}</dt>
							<dd class="text-fg">{{ datetime(job.scheduled_date) }}</dd>
						</div>
						<div>
							<dt class="text-fg-muted">{{ t("الفني", "Technician") }}</dt>
							<dd class="text-fg">
								{{ job.primary_technician || t("غير مسند", "Unassigned") }}
							</dd>
						</div>
						<div>
							<dt class="text-fg-muted">{{ t("فريق الخدمة", "Service Team") }}</dt>
							<dd class="text-fg">
								{{ job.assigned_service_team || t("غير مسند", "Unassigned")
								}}<span v-if="job.team_leader" class="text-fg-muted">
									· {{ t("القائد", "Lead") }}: {{ job.team_leader }}</span
								>
							</dd>
						</div>
						<div>
							<dt class="text-fg-muted">
								{{ t("اتفاقية زمن الاستجابة", "Response SLA") }}
							</dt>
							<dd class="text-fg">
								<span v-if="job.responded_on" class="text-success"
									>{{ t("تمت الاستجابة", "Responded") }}
									{{ datetime(job.responded_on) }}</span
								>
								<span
									v-else-if="job.sla_breached"
									class="inline-flex items-center gap-1 font-medium text-danger"
								>
									<span
										class="size-1.5 rounded-full bg-danger"
										aria-hidden="true"
									/>
									{{ t("متجاوزة · الاستحقاق", "Breached · due") }}
									{{ datetime(job.promised_response_by) }}
								</span>
								<span v-else-if="job.promised_response_by"
									>{{ t("الاستحقاق", "Due") }}
									{{ datetime(job.promised_response_by) }}</span
								>
								<span v-else class="text-fg-muted">—</span>
							</dd>
						</div>
						<div>
							<dt class="text-fg-muted">{{ t("الأولوية", "Priority") }}</dt>
							<dd class="text-fg">{{ showPriority(job.priority) }}</dd>
						</div>
						<div>
							<dt class="text-fg-muted">{{ t("نوع الخدمة", "Service type") }}</dt>
							<dd class="text-fg">{{ job.service_type || "—" }}</dd>
						</div>
						<div>
							<dt class="text-fg-muted">{{ t("العنوان", "Address") }}</dt>
							<dd class="whitespace-pre-line text-fg">
								{{ job.address_display || "—" }}
							</dd>
						</div>
					</dl>

					<div class="border-t border-border pt-3">
						<p class="mb-1 text-fg-muted">{{ t("الفاتورة", "Invoice") }}</p>
						<p v-if="job.sales_invoice" class="font-mono text-sm text-brand">
							{{ job.sales_invoice }}
						</p>
						<button
							v-else
							type="button"
							:disabled="invoicing || !job.items?.length"
							class="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-border bg-surface px-4 py-2 text-sm font-medium text-fg transition-colors hover:bg-bg-subtle disabled:opacity-50"
							@click="generateInvoice"
						>
							<Spinner v-if="invoicing" :size="16" />
							{{
								invoicing
									? t("جارٍ الإنشاء…", "Creating…")
									: t("إنشاء فاتورة", "Create invoice")
							}}
						</button>
					</div>

					<!-- Customer feedback (Feature 12) -->
					<div class="border-t border-border pt-3">
						<p class="mb-1 text-fg-muted">
							{{ t("التغذية الراجعة من العميل", "Customer feedback") }}
						</p>
						<div v-if="feedback">
							<p class="text-lg" :aria-label="t('التقييم', 'rating')">
								<span class="text-warning">{{ "★".repeat(feedback.rating) }}</span>
								<span class="text-fg-muted">{{
									"★".repeat(5 - feedback.rating)
								}}</span>
								<span
									v-if="feedback.nps_score != null"
									class="ml-2 align-middle text-xs text-fg-muted"
								>
									NPS {{ feedback.nps_score }}
								</span>
							</p>
							<p v-if="feedback.comments" class="mt-1 text-sm text-fg">
								“{{ feedback.comments }}”
							</p>
						</div>
						<p v-else class="text-sm text-fg-muted">
							{{
								job.status === "Completed"
									? t("بانتظار تقييم العميل.", "Awaiting customer rating.")
									: t(
											"متاحة بعد إتمام أمر الخدمة.",
											"Available after the job is completed.",
										)
							}}
						</p>
					</div>

					<div
						v-if="job.status !== 'Completed' && job.status !== 'Cancelled'"
						class="border-t border-border pt-3"
					>
						<div class="mb-2 flex items-center justify-between">
							<p class="text-fg-muted">
								{{
									job.primary_technician
										? t("إعادة إسناد الفني", "Reassign technician")
										: t("إسناد فني", "Assign technician")
								}}
							</p>
							<button
								type="button"
								:disabled="loadingSuggestions"
								class="text-xs font-medium text-brand hover:underline disabled:opacity-50"
								@click="loadSuggestions"
							>
								{{
									loadingSuggestions
										? t("جارٍ البحث…", "Finding…")
										: t("اقتراح", "Suggest")
								}}
							</button>
						</div>

						<p v-if="assignError" class="mb-2 text-xs text-danger">{{ assignError }}</p>

						<ul v-if="suggestions.length" class="space-y-2">
							<li
								v-for="s in suggestions"
								:key="s.technician"
								class="rounded-xl border border-border bg-white/2 p-2.5"
							>
								<div class="flex items-center justify-between gap-2">
									<div class="min-w-0">
										<p class="truncate text-sm font-medium text-fg">
											{{ s.technician_name }}
										</p>
										<p class="truncate text-xs text-fg-muted">
											{{ s.reasons.join(" · ") || s.status }}
										</p>
									</div>
									<button
										type="button"
										:disabled="assigningTo !== null"
										class="kl-grad-brand inline-flex shrink-0 items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-white shadow-e2 transition-[filter] hover:brightness-110 disabled:opacity-60"
										@click="assign(s.technician)"
									>
										<Spinner v-if="assigningTo === s.technician" :size="12" />
										{{ t("إسناد", "Assign") }}
									</button>
								</div>
							</li>
						</ul>
						<p v-else-if="!loadingSuggestions" class="text-xs text-fg-muted">
							{{
								t(
									"اضغط «اقتراح» لترتيب الفنيين المتاحين حسب المهارة والمنطقة والقرب.",
									"Tap “Suggest” to rank available technicians by skill, territory and proximity.",
								)
							}}
						</p>
					</div>

					<div
						v-if="job.status !== 'Completed' && job.status !== 'Cancelled'"
						class="border-t border-border pt-3"
					>
						<div class="mb-2 flex items-center justify-between">
							<p class="text-fg-muted">
								{{
									job.assigned_service_team
										? t("إعادة إسناد الفريق", "Reassign team")
										: t("إسناد فريق", "Assign team")
								}}
							</p>
							<button
								type="button"
								:disabled="loadingTeamSuggestions"
								class="text-xs font-medium text-brand hover:underline disabled:opacity-50"
								@click="loadTeamSuggestions"
							>
								{{
									loadingTeamSuggestions
										? t("جارٍ البحث…", "Finding…")
										: t("اقتراح", "Suggest")
								}}
							</button>
						</div>

						<p v-if="teamAssignError" class="mb-2 text-xs text-danger">
							{{ teamAssignError }}
						</p>

						<ul v-if="teamSuggestions.length" class="space-y-2">
							<li
								v-for="s in teamSuggestions"
								:key="s.team"
								class="rounded-xl border border-border bg-white/2 p-2.5"
							>
								<div class="flex items-center justify-between gap-2">
									<div class="min-w-0">
										<p class="truncate text-sm font-medium text-fg">
											{{ s.team_name }}
										</p>
										<p class="truncate text-xs text-fg-muted">
											{{ s.reasons.join(" · ") || s.territory || "—" }}
										</p>
									</div>
									<button
										type="button"
										:disabled="assigningTeamTo !== null"
										class="kl-grad-brand inline-flex shrink-0 items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-white shadow-e2 transition-[filter] hover:brightness-110 disabled:opacity-60"
										@click="assignTeamTo(s.team)"
									>
										<Spinner v-if="assigningTeamTo === s.team" :size="12" />
										{{ t("إسناد", "Assign") }}
									</button>
								</div>
							</li>
						</ul>
						<p v-else-if="!loadingTeamSuggestions" class="text-xs text-fg-muted">
							{{
								t(
									"اضغط «اقتراح» لترتيب فرق الخدمة حسب المهارة والمنطقة والسعة.",
									"Tap “Suggest” to rank service teams by skill, territory and capacity.",
								)
							}}
						</p>
					</div>
				</aside>
			</div>
		</div>

		<!-- Transient action errors surface as a bottom toast (user request):
		     always visible regardless of scroll position, never pushing the
		     page header around. The fatal load error keeps its full-page block. -->
		<div
			v-if="error && job"
			class="pointer-events-none fixed inset-x-0 bottom-6 z-50 flex justify-center px-4"
		>
			<p
				class="pointer-events-auto rounded-xl border border-danger/30 bg-danger/10 px-4 py-2.5 text-sm font-medium text-danger shadow-card backdrop-blur"
			>
				{{ error }}
			</p>
		</div>
	</div>
</template>

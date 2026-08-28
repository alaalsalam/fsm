<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import type {
	EquipmentInspection,
	InspectionTemplateSummary,
	JobEquipmentRow,
	MaterialPlan,
	ServiceReport,
} from "@digit/api";
import {
	IonPage,
	IonHeader,
	IonToolbar,
	IonTitle,
	IonButtons,
	IonBackButton,
	IonContent,
	IonSpinner,
} from "@ionic/vue";
import { Camera, CameraResultType, CameraSource } from "@capacitor/camera";
import { ChecklistItem, KlButton } from "@digit/ui";
import { formatNumber, statusLabel, t } from "@digit/ui";
import {
	startTimer,
	stopTimer,
	getJob,
	getJobVisits,
	runVisitCommand,
	installedBase,
	inspectionsApi,
	materialsApi,
	reportingApi,
	type MobileJob,
	type MobileVisit,
} from "@/lib/fsm";
import { Network } from "@capacitor/network";
import { cacheGet, cachePut, createOfflineCommand, enqueue, mediaPut } from "@/lib/offline";

const props = defineProps<{ id: string }>();

const timerRunning = ref(false);
const timerBusy = ref(false);
const elapsed = ref(0);
const lastHours = ref<number | null>(null);
const timerError = ref("");
const job = ref<MobileJob>();
const visits = ref<MobileVisit[]>([]);
const equipment = ref<JobEquipmentRow[]>([]);
const templates = ref<InspectionTemplateSummary[]>([]);
const inspections = ref<EquipmentInspection[]>([]);
const materialPlan = ref<MaterialPlan>();
const reports = ref<ServiceReport[]>([]);
const loading = ref(true);
const actionBusy = ref(false);
const actionError = ref("");
let startedAt = 0;
let tick: ReturnType<typeof setInterval> | undefined;

const clock = (s: number) => {
	const h = Math.floor(s / 3600)
		.toString()
		.padStart(2, "0");
	const m = Math.floor((s % 3600) / 60)
		.toString()
		.padStart(2, "0");
	const sec = Math.floor(s % 60)
		.toString()
		.padStart(2, "0");
	return `${h}:${m}:${sec}`;
};
const responseTypeLabel = (value: string) =>
	({
		"Yes/No": t("نعم / لا", "Yes / No"),
		"Pass/Fail": t("ناجح / فاشل", "Pass / Fail"),
		Number: t("رقم", "Number"),
		Text: t("نص", "Text"),
		Select: t("اختيار", "Select"),
		Date: t("تاريخ", "Date"),
		Photo: t("صورة", "Photo"),
		Signature: t("توقيع", "Signature"),
		Measurement: t("قياس", "Measurement"),
	})[value] || value;

async function toggleTimer() {
	timerBusy.value = true;
	timerError.value = "";
	try {
		if (timerRunning.value) {
			const res = await stopTimer(props.id);
			lastHours.value = res.actual_hours;
			timerRunning.value = false;
			clearInterval(tick);
			elapsed.value = 0;
		} else {
			await startTimer(props.id);
			timerRunning.value = true;
			startedAt = Date.now();
			tick = setInterval(() => (elapsed.value = (Date.now() - startedAt) / 1000), 1000);
		}
	} catch {
		timerError.value = t(
			"تعذر تحديث المؤقت. تحقق من الاتصال.",
			"Couldn't update the timer. Check your connection.",
		);
	} finally {
		timerBusy.value = false;
	}
}

onMounted(async () => {
	try {
		[job.value, visits.value, equipment.value, templates.value, inspections.value] =
			await Promise.all([
				getJob(props.id),
				getJobVisits(props.id),
				installedBase.getJobEquipment(props.id),
				inspectionsApi.listTemplates({ status: "Active" }),
				inspectionsApi.list({ service_job: props.id }),
			]);
		materialPlan.value = await materialsApi.plan(props.id).catch(() => undefined);
		reports.value = (
			await reportingApi.list(props.id).catch(() => ({ reports: [], certificates: [] }))
		).reports;
		await cachePut(`job:${props.id}`, {
			job: job.value,
			visits: visits.value,
			equipment: equipment.value,
		});
	} catch {
		const cached = await cacheGet<{
			job: MobileJob;
			visits: MobileVisit[];
			equipment: JobEquipmentRow[];
		}>(`job:${props.id}`);
		if (cached) {
			job.value = cached.job;
			visits.value = cached.visits;
			equipment.value = cached.equipment;
		} else
			actionError.value = t(
				"تعذر تحميل هذا العمل من الخادم.",
				"Couldn't load this job from the server.",
			);
	} finally {
		loading.value = false;
	}
});
onUnmounted(() => clearInterval(tick));

const commandByStatus: Record<string, string> = {
	Dispatched: "start_travel",
	"En Route": "check_in_visit",
	"Checked In": "start_visit_work",
	"In Progress": "check_out_visit",
	"Checked Out": "complete_visit",
};
async function advance(visit: MobileVisit) {
	const command = commandByStatus[visit.status];
	if (!command) return;
	actionBusy.value = true;
	actionError.value = "";
	const connected = (await Network.getStatus()).connected;
	try {
		if (!connected) throw new TypeError("offline");
		await runVisitCommand(command, visit.name);
		visits.value = await getJobVisits(props.id);
		job.value = await getJob(props.id);
	} catch {
		if (connected) {
			actionError.value = t(
				"رفض الخادم هذا التغيير. حدّث العمل وتحقق من الإسناد.",
				"The server rejected this change. Refresh the job and check your assignment.",
			);
			return;
		}
		const actionByCommand: Record<string, string> = {
			start_travel: "visit.start_travel",
			check_in_visit: "visit.check_in",
			start_visit_work: "visit.start_work",
			check_out_visit: "visit.check_out",
			complete_visit: "visit.complete",
		};
		await enqueue(
			createOfflineCommand({
				entity_type: "Service Visit",
				entity_id: visit.name,
				expected_version: visit.modified,
				action: actionByCommand[command]!,
				payload: {},
			}),
		);
		actionError.value = t(
			"حُفظ دون اتصال وستتم مزامنة تغيير الزيارة تلقائيًا.",
			"Saved offline. This visit change will sync automatically.",
		);
	} finally {
		actionBusy.value = false;
	}
}

const photos = ref<string[]>([]);
const workflowMessage = ref("");
const signatureCanvas = ref<HTMLCanvasElement>();
let drawing = false;

function signaturePoint(event: PointerEvent) {
	const canvas = signatureCanvas.value;
	if (!canvas) return;
	const rect = canvas.getBoundingClientRect();
	return {
		x: (event.clientX - rect.left) * (canvas.width / rect.width),
		y: (event.clientY - rect.top) * (canvas.height / rect.height),
	};
}

function startSignature(event: PointerEvent) {
	const point = signaturePoint(event);
	const context = signatureCanvas.value?.getContext("2d");
	if (!point || !context) return;
	drawing = true;
	context.beginPath();
	context.moveTo(point.x, point.y);
}

function drawSignature(event: PointerEvent) {
	if (!drawing) return;
	const point = signaturePoint(event);
	const context = signatureCanvas.value?.getContext("2d");
	if (!point || !context) return;
	context.strokeStyle = "#e8fff7";
	context.lineWidth = 3;
	context.lineCap = "round";
	context.lineTo(point.x, point.y);
	context.stroke();
}

async function saveSignature() {
	const report = reports.value.find((row) => row.status === "Customer Review");
	const data = signatureCanvas.value?.toDataURL("image/png");
	if (!report || !data) {
		workflowMessage.value = t(
			"جهّز التقرير والتقط التوقيع أولًا.",
			"Prepare the report and capture the signature first.",
		);
		return;
	}
	await mediaPut(`signature:${report.name}`, data);
	const connected = (await Network.getStatus()).connected;
	if (!connected) {
		await enqueue(
			createOfflineCommand({
				entity_type: "Service Report",
				entity_id: report.name,
				expected_version: report.modified,
				action: "report.update",
				payload: { customer_signature: data },
			}),
		);
		await enqueue(
			createOfflineCommand({
				entity_type: "Service Report",
				entity_id: report.name,
				expected_version: report.modified,
				action: "report.transition",
				payload: { status: "Customer Signed" },
			}),
		);
		workflowMessage.value = t(
			"حُفظ التوقيع محليًا وأضيف إلى طابور المزامنة.",
			"Signature saved locally and queued for sync.",
		);
		return;
	}
	try {
		await reportingApi.update(report.name, { customer_signature: data });
		await reportingApi.transition(report.name, "Customer Signed");
		workflowMessage.value = t("تم التقاط توقيع العميل.", "Customer signature captured.");
	} catch {
		workflowMessage.value = t("تعذر إرسال التوقيع.", "Signature could not be submitted.");
	}
}

async function beginInspection(row: JobEquipmentRow) {
	if (!templates.value.length) {
		workflowMessage.value = t(
			"لا يوجد نموذج فحص نشط.",
			"No active inspection template is available.",
		);
		return;
	}
	actionBusy.value = true;
	try {
		const created = await inspectionsApi.start({
			service_job: props.id,
			installed_equipment: row.installed_equipment,
			inspection_template: templates.value[0]!.name,
			service_visit: visits.value[0]?.name,
		});
		inspections.value.unshift(created);
	} catch {
		workflowMessage.value = t(
			"تعذر بدء الفحص. تحقق من الإسناد ونطاق النموذج.",
			"Inspection could not be started. Check assignment and template scope.",
		);
	} finally {
		actionBusy.value = false;
	}
}

async function saveInspection(inspection: EquipmentInspection, complete = false) {
	actionBusy.value = true;
	try {
		const responses = inspection.results.map((row) => ({
			item_code: row.item_code,
			response_value: row.response_value,
			numeric_value: row.numeric_value,
			date_value: row.date_value,
			attachment: row.attachment,
			signature: row.signature,
			evidence: row.evidence,
		}));
		const connected = (await Network.getStatus()).connected;
		if (!connected) {
			await enqueue(
				createOfflineCommand({
					entity_type: "Equipment Inspection",
					entity_id: inspection.name,
					expected_version: inspection.modified,
					action: "inspection.save",
					payload: { responses },
				}),
			);
			if (complete)
				await enqueue(
					createOfflineCommand({
						entity_type: "Equipment Inspection",
						entity_id: inspection.name,
						expected_version: inspection.modified,
						action: "inspection.complete",
						payload: {},
					}),
				);
			workflowMessage.value = t(
				"حُفظ الفحص دون اتصال وأضيف إلى طابور المزامنة.",
				"Inspection saved offline and queued for sync.",
			);
			return;
		}
		await inspectionsApi.save(inspection.name, responses);
		if (complete) await inspectionsApi.complete(inspection.name);
		inspections.value = await inspectionsApi.list({ service_job: props.id });
	} catch {
		workflowMessage.value = t(
			"فشل التحقق من الفحص. أكمل الإجابات والأدلة المطلوبة.",
			"Inspection validation failed. Complete required responses and evidence.",
		);
	} finally {
		actionBusy.value = false;
	}
}

async function consume(row: MaterialPlan["items"][number]) {
	try {
		await materialsApi.move(
			props.id,
			"Consume",
			[
				{
					item_code: row.item_code,
					qty: Math.max(row.required_qty - row.consumed_qty, 1),
					installed_equipment: row.installed_equipment,
				},
			],
			{
				service_visit: visits.value[0]?.name,
				source_warehouse: materialPlan.value?.warehouse,
			},
		);
		materialPlan.value = await materialsApi.plan(props.id);
	} catch {
		workflowMessage.value = t(
			"رُفض استهلاك المواد؛ تحقق من الكمية المصروفة ومستودع المركبة.",
			"Material consumption was rejected; verify issued quantity and van warehouse.",
		);
	}
}

async function prepareSignatureReport() {
	try {
		let report = reports.value.find((row) => row.status === "Customer Review");
		if (!report) {
			report = await reportingApi.generate(props.id, "Service Report", crypto.randomUUID());
			report = await reportingApi.transition(report.name, "Generated");
			report = await reportingApi.transition(report.name, "Customer Review");
			reports.value.unshift(report);
		}
		workflowMessage.value = `${t("التقرير", "Report")} ${report.name} ${t("جاهز لتوقيع العميل.", "is ready for customer signature.")}`;
	} catch {
		workflowMessage.value = t(
			"تعذر تجهيز تقرير العميل.",
			"The customer report could not be prepared.",
		);
	}
}

async function addPhoto() {
	try {
		const photo = await Camera.getPhoto({
			quality: 70,
			resultType: CameraResultType.DataUrl,
			source: CameraSource.Camera,
		});
		if (photo.dataUrl) photos.value.push(photo.dataUrl);
		if (photo.dataUrl)
			await mediaPut(`photo:${props.id}:${crypto.randomUUID()}`, photo.dataUrl);
	} catch {
		// User cancelled or no camera (e.g. browser dev) — ignore.
	}
}
</script>

<template>
	<IonPage>
		<IonHeader>
			<IonToolbar>
				<IonButtons slot="start">
					<IonBackButton default-href="/jobs" />
				</IonButtons>
				<IonTitle>{{ id }}</IonTitle>
			</IonToolbar>
		</IonHeader>
		<IonContent :fullscreen="true">
			<div class="space-y-6 p-4">
				<IonSpinner v-if="loading" />
				<p v-if="actionError" class="text-sm text-danger">{{ actionError }}</p>
				<section v-if="job" class="rounded-lg border border-border bg-bg p-4">
					<h2 class="text-lg font-bold">{{ job.customer_name || job.customer }}</h2>
					<p class="text-sm text-fg-muted">
						{{ statusLabel(job.status) }} · {{ statusLabel(job.phase || "Planning") }}
					</p>
					<p class="mt-2 text-sm">{{ job.address_display }}</p>
				</section>
				<section v-if="visits.length">
					<h2 class="mb-2 text-lg font-bold">
						{{ t("زيارات الخدمة", "Service visits") }}
					</h2>
					<div
						v-for="visit in visits"
						:key="visit.name"
						class="mb-2 rounded-lg border border-border bg-bg p-4"
					>
						<div class="flex items-center justify-between">
							<div>
								<p class="font-semibold">
									{{ t("زيارة", "Visit") }} {{ formatNumber(visit.visit_number) }}
								</p>
								<p class="text-sm text-fg-muted">{{ statusLabel(visit.status) }}</p>
							</div>
							<button
								v-if="commandByStatus[visit.status]"
								class="rounded-lg bg-brand px-3 py-2 text-sm font-semibold text-white"
								:disabled="actionBusy"
								@click="advance(visit)"
							>
								{{ t("متابعة", "Continue") }}
							</button>
						</div>
					</div>
				</section>
				<section>
					<h2 class="mb-2 text-lg font-bold">
						{{ t("المعدات المرتبطة", "Linked equipment") }}
					</h2>
					<p
						v-if="!equipment.length"
						class="rounded-lg border border-dashed border-border p-4 text-sm text-fg-muted"
					>
						{{
							t(
								"لا توجد معدات مركبة مرتبطة بهذا العمل.",
								"No installed equipment linked to this job.",
							)
						}}
					</p>
					<RouterLink
						v-for="row in equipment"
						:key="row.installed_equipment"
						:to="`/equipment/${row.installed_equipment}`"
						class="mb-2 block rounded-lg border border-border bg-bg p-4"
					>
						<div class="flex items-center justify-between gap-3">
							<div>
								<p class="font-mono font-semibold">{{ row.installed_equipment }}</p>
								<p class="text-sm text-fg-muted">
									{{ row.item_code
									}}<span v-if="row.serial_no"> · {{ row.serial_no }}</span>
								</p>
							</div>
							<span class="text-xs text-brand">{{
								statusLabel(row.equipment_status)
							}}</span>
						</div>
					</RouterLink>
					<button
						v-for="row in equipment"
						:key="`inspect-${row.installed_equipment}`"
						type="button"
						class="mb-2 w-full rounded-lg border border-brand/40 px-3 py-2 text-sm text-brand"
						@click="beginInspection(row)"
					>
						{{ t("بدء الفحص", "Start inspection") }}
					</button>
				</section>
				<section v-if="inspections.length">
					<h2 class="mb-2 text-lg font-bold">{{ t("الفحوصات", "Inspections") }}</h2>
					<div
						v-for="inspection in inspections"
						:key="inspection.name"
						class="mb-3 rounded-lg border border-border bg-bg p-4"
					>
						<p class="font-semibold">
							{{ inspection.installed_equipment }} ·
							{{ statusLabel(inspection.overall_result) }}
						</p>
						<label
							v-for="result in inspection.results"
							:key="result.item_code"
							class="mt-3 block text-sm"
						>
							<span class="mb-1 block text-fg-muted"
								>{{ result.label }}{{ result.required ? " *" : "" }}</span
							>
							<input
								v-if="
									result.response_type === 'Number' ||
									result.response_type === 'Measurement'
								"
								v-model.number="result.numeric_value"
								type="number"
								class="w-full rounded-lg border border-border bg-transparent p-2"
							/>
							<input
								v-else
								v-model="result.response_value"
								class="w-full rounded-lg border border-border bg-transparent p-2"
								:placeholder="responseTypeLabel(result.response_type)"
							/>
						</label>
						<div v-if="inspection.status === 'In Progress'" class="mt-3 flex gap-2">
							<button
								class="rounded-lg border border-brand px-3 py-2 text-sm text-brand"
								@click="saveInspection(inspection)"
							>
								{{ t("حفظ", "Save") }}</button
							><button
								class="rounded-lg bg-brand px-3 py-2 text-sm font-semibold text-white"
								@click="saveInspection(inspection, true)"
							>
								{{ t("إكمال", "Complete") }}
							</button>
						</div>
					</div>
				</section>
				<section v-if="materialPlan?.items?.length">
					<h2 class="mb-2 text-lg font-bold">{{ t("المواد", "Materials") }}</h2>
					<div
						v-for="row in materialPlan.items"
						:key="row.requirement_row"
						class="mb-2 flex items-center justify-between rounded-lg border border-border p-3"
					>
						<div>
							<p>{{ row.item_name || row.item_code }}</p>
							<p class="text-xs text-fg-muted">
								{{ t("المتاح", "Available") }}
								{{ formatNumber(row.available_qty) }} · {{ t("المستخدم", "Used") }}
								{{ formatNumber(row.consumed_qty) }}/{{
									formatNumber(row.required_qty)
								}}
							</p>
						</div>
						<button
							class="rounded-lg border border-brand px-3 py-2 text-xs text-brand"
							@click="consume(row)"
						>
							{{ t("استهلاك", "Consume") }}
						</button>
					</div>
				</section>
				<section class="rounded-lg border border-border bg-bg p-4">
					<div class="flex items-center justify-between">
						<div>
							<h2 class="text-lg font-bold">{{ t("مؤقت العمل", "Labour timer") }}</h2>
							<p
								class="font-mono text-2xl tabular-nums"
								:class="timerRunning ? 'text-brand' : 'text-fg-muted'"
							>
								{{
									timerRunning
										? clock(elapsed)
										: lastHours != null
											? `${formatNumber(lastHours)} ${t("ساعة مسجلة", "hours logged")}`
											: "00:00:00"
								}}
							</p>
						</div>
						<button
							type="button"
							:disabled="timerBusy"
							class="inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold transition-[filter] disabled:opacity-60"
							:class="
								timerRunning
									? 'border border-danger/40 text-danger'
									: 'kl-grad-brand text-white shadow-e2 hover:brightness-110'
							"
							@click="toggleTimer"
						>
							<IonSpinner v-if="timerBusy" name="crescent" class="size-4" />
							{{ timerRunning ? t("إيقاف", "Stop") : t("بدء", "Start") }}
						</button>
					</div>
					<p v-if="timerError" class="mt-2 text-xs text-danger">{{ timerError }}</p>
				</section>

				<section>
					<h2 class="mb-2 text-lg font-bold">{{ t("قائمة التحقق", "Checklist") }}</h2>
					<div class="rounded-lg border border-border bg-bg">
						<ChecklistItem
							v-for="(item, i) in job?.tasks || []"
							:key="i"
							:model-value="item.status === 'Done'"
							:label="item.task"
							:note="item.note"
							@update:model-value="() => {}"
						/>
					</div>
				</section>

				<section>
					<h2 class="mb-2 text-lg font-bold">{{ t("الصور", "Photos") }}</h2>
					<div class="grid grid-cols-3 gap-2">
						<img
							v-for="(src, i) in photos"
							:key="i"
							:src="src"
							class="aspect-square w-full rounded-md object-cover"
						/>
						<button
							type="button"
							class="flex aspect-square items-center justify-center rounded-md border border-dashed border-border text-fg-muted"
							@click="addPhoto"
						>
							+ {{ t("إضافة", "Add") }}
						</button>
					</div>
				</section>

				<section>
					<h2 class="mb-2 text-lg font-bold">{{ t("التوقيع", "Signature") }}</h2>
					<button
						type="button"
						class="w-full rounded-lg border border-brand px-3 py-3 text-brand"
						@click="prepareSignatureReport"
					>
						{{ t("تجهيز تقرير توقيع العميل", "Prepare customer signature report") }}
					</button>
					<canvas
						ref="signatureCanvas"
						width="640"
						height="240"
						class="mt-2 h-32 w-full touch-none rounded-lg border border-dashed border-border bg-black/20"
						@pointerdown="startSignature"
						@pointermove="drawSignature"
						@pointerup="drawing = false"
						@pointerleave="drawing = false"
					/>
					<button
						type="button"
						class="mt-2 w-full rounded-lg bg-brand px-3 py-3 font-semibold text-white"
						@click="saveSignature"
					>
						{{ t("حفظ التوقيع", "Save signature") }}
					</button>
				</section>
				<p
					v-if="workflowMessage"
					class="rounded-lg border border-border p-3 text-sm text-fg-muted"
				>
					{{ workflowMessage }}
				</p>

				<KlButton block>{{ t("إكمال العمل", "Complete job") }}</KlButton>
			</div>
		</IonContent>
	</IonPage>
</template>

// Service Report is command-owned by design (snapshot integrity, immutability
// after Submitted, revision discipline). The desk form therefore never saves
// directly — it drives the official fsm.reporting commands instead, so the
// "must use the command API" guard can no longer be hit from this screen.

const REPORT_TRANSITIONS = {
	Draft: ["Generated"],
	Generated: ["Customer Review"],
	"Customer Review": ["Customer Signed"],
	"Customer Signed": ["Verified"],
	Verified: ["Submitted"],
};

const REPORT_STATUS_AR = {
	Generated: "مُولّد",
	"Customer Review": "مراجعة العميل",
	"Customer Signed": "موقّع من العميل",
	Verified: "مُدقّق",
	Submitted: "معتمد نهائي",
};

function reportCall(frm, method, args) {
	frappe.call({
		method,
		args,
		freeze: true,
		callback: () => frm.reload_doc(),
		error: (r) => frappe.msgprint(r?.message || __("تعذّر تنفيذ الإجراء.")),
	});
}

frappe.ui.form.on("Service Report", {
	refresh(frm) {
		frm.disable_save();

		if (frm.is_new()) {
			frm.set_intro(
				__("تقارير الخدمة تُولَّد من أمر خدمة عبر الزر أدناه — لا تُنشأ يدويًا."),
				"blue",
			);
			frm.add_custom_button(__("توليد من أمر خدمة"), () => {
				const dialog = new frappe.ui.Dialog({
					title: __("توليد تقرير خدمة"),
					fields: [
						{
							fieldname: "service_job",
							fieldtype: "Link",
							options: "Service Job",
							label: __("أمر الخدمة"),
							reqd: 1,
						},
					],
					primary_action_label: __("توليد"),
					primary_action(values) {
						dialog.hide();
						frappe.call({
							method: "fsm.reporting.generate_service_report",
							args: { service_job: values.service_job },
							freeze: true,
							callback: (r) => {
								if (r.message?.name)
									frappe.set_route("Form", "Service Report", r.message.name);
							},
							error: (r) =>
								frappe.msgprint(r?.message || __("تعذّر توليد التقرير.")),
						});
					},
				});
				dialog.show();
			}).addClass("btn-primary");
			return;
		}

		frm.set_intro(
			__("هذا المستند تديره أوامر التطبيق: استخدم أزرار «إجراءات التقرير» بدل الحفظ المباشر."),
			"blue",
		);

		const editable = !["Verified", "Submitted"].includes(frm.doc.status);
		if (editable) {
			frm.add_custom_button(
				__("تحديث الحقول"),
				() => {
					const dialog = new frappe.ui.Dialog({
						title: __("تحديث تقرير الخدمة"),
						fields: [
							{
								fieldname: "work_performed",
								fieldtype: "Text",
								label: __("الأعمال المنفذة"),
								default: frm.doc.work_performed,
							},
							{
								fieldname: "recommendations",
								fieldtype: "Text",
								label: __("التوصيات"),
								default: frm.doc.recommendations,
							},
							{
								fieldname: "customer_name",
								fieldtype: "Data",
								label: __("اسم ممثل العميل"),
								default: frm.doc.customer_name,
							},
						],
						primary_action_label: __("حفظ"),
						primary_action(values) {
							dialog.hide();
							reportCall(frm, "fsm.reporting.update_service_report", {
								service_report: frm.doc.name,
								...values,
							});
						},
					});
					dialog.show();
				},
				__("إجراءات التقرير"),
			);
		}

		(REPORT_TRANSITIONS[frm.doc.status] || []).forEach((next) => {
			frm.add_custom_button(
				__("الانتقال إلى: {0}", [REPORT_STATUS_AR[next] || next]),
				() =>
					reportCall(frm, "fsm.reporting.transition_service_report", {
						service_report: frm.doc.name,
						status: next,
					}),
				__("إجراءات التقرير"),
			);
		});

		if (frm.doc.status === "Submitted") {
			frm.add_custom_button(
				__("إنشاء مراجعة جديدة"),
				() =>
					reportCall(frm, "fsm.reporting.revise_service_report", {
						service_report: frm.doc.name,
						generation_key: `${frm.doc.name}-rev-${frm.doc.revision + 1}`,
					}),
				__("إجراءات التقرير"),
			);
		}
	},
});

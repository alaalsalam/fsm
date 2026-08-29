// Service Certificate is command-owned (issued from a Submitted Service Report,
// revocable with a reason — never edited directly). The desk form drives the
// official fsm.reporting commands so the guard is unreachable from here.
frappe.ui.form.on("Service Certificate", {
	refresh(frm) {
		frm.disable_save();

		if (frm.is_new()) {
			frm.set_intro(
				__("الشهادات تُصدر من تقرير خدمة معتمد نهائي عبر الزر أدناه — لا تُنشأ يدويًا."),
				"blue",
			);
			frm.add_custom_button(__("إصدار من تقرير خدمة"), () => {
				const dialog = new frappe.ui.Dialog({
					title: __("إصدار شهادة خدمة"),
					fields: [
						{
							fieldname: "service_report",
							fieldtype: "Link",
							options: "Service Report",
							label: __("تقرير الخدمة (معتمد نهائي)"),
							reqd: 1,
							get_query: () => ({ filters: { status: "Submitted" } }),
						},
						{
							fieldname: "certificate_type",
							fieldtype: "Select",
							options: "Refill Certificate\nHydro Test Certificate",
							label: __("نوع الشهادة"),
							reqd: 1,
						},
						{
							fieldname: "installed_equipment",
							fieldtype: "Link",
							options: "Installed Equipment",
							label: __("المعدة (اختياري)"),
						},
					],
					primary_action_label: __("إصدار"),
					primary_action(values) {
						dialog.hide();
						frappe.call({
							method: "fsm.reporting.issue_service_certificate",
							args: values,
							freeze: true,
							callback: (r) => {
								if (r.message?.name)
									frappe.set_route("Form", "Service Certificate", r.message.name);
							},
							error: (r) => frappe.msgprint(r?.message || __("تعذّر إصدار الشهادة.")),
						});
					},
				});
				dialog.show();
			}).addClass("btn-primary");
			return;
		}

		frm.set_intro(
			__("هذا المستند تديره أوامر التطبيق — الشهادة لا تُعدّل، ويمكن إبطالها بسبب موثق."),
			"blue",
		);

		if (frm.doc.status === "Issued") {
			frm.add_custom_button(__("إبطال الشهادة"), () => {
				frappe.prompt(
					{
						fieldname: "reason",
						fieldtype: "Small Text",
						label: __("سبب الإبطال"),
						reqd: 1,
					},
					(values) => {
						frappe.call({
							method: "fsm.reporting.revoke_service_certificate",
							args: { service_certificate: frm.doc.name, reason: values.reason },
							freeze: true,
							callback: () => frm.reload_doc(),
							error: (r) => frappe.msgprint(r?.message || __("تعذّر إبطال الشهادة.")),
						});
					},
					__("إبطال الشهادة"),
					__("إبطال"),
				);
			});
		}
	},
});

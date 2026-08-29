frappe.ui.form.on("Service Job", {
	refresh(frm) {
		if (frm.is_new()) return;
		load_job_guidance(frm);
		if (["Draft", "Planned", "Scheduled"].includes(frm.doc.status)) {
			frm.add_custom_button(
				__("Schedule and create visit"),
				() => schedule_with_visit(frm),
				__("Next step"),
			);
		}
		frm.add_custom_button(
			__("Open visits"),
			() => {
				frappe.set_route("List", "Service Visit", { service_job: frm.doc.name });
			},
			__("Related records"),
		);
		if (frm.doc.status === "Completed") {
			frm.add_custom_button(
				__("Generate / open Service Report"),
				() => generate_report(frm),
				__("Next step"),
			);
			frm.add_custom_button(
				__("Create / open Sales Invoice"),
				() => create_invoice(frm),
				__("Billing"),
			);
			frm.add_custom_button(
				__("Create / open Quotation"),
				() => create_quotation(frm),
				__("Billing"),
			);
		}
	},
});

async function load_job_guidance(frm) {
	try {
		const { message } = await frappe.call({
			method: "fsm.process.api.get_job_hub",
			args: { service_job: frm.doc.name },
		});
		const blockers = (message.completion_blockers || [])
			.map((row) => row.message || row)
			.join(" • ");
		frm.set_intro(
			blockers || message.next_action?.message || __("Continue the Service Job workflow."),
			blockers ? "orange" : "blue",
		);
	} catch (error) {
		console.warn("Unable to load Service Job guidance", error);
	}
}

function schedule_with_visit(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Schedule and create visit"),
		fields: [
			{
				fieldname: "scheduled_start",
				fieldtype: "Datetime",
				label: __("Scheduled Start"),
				reqd: 1,
				default: frm.doc.scheduled_date,
			},
			{
				fieldname: "scheduled_end",
				fieldtype: "Datetime",
				label: __("Scheduled End"),
				default: frm.doc.scheduled_end,
			},
			{
				fieldname: "service_team",
				fieldtype: "Link",
				options: "Service Team",
				label: __("Assigned Service Team"),
				default: frm.doc.assigned_service_team,
				get_query: () => ({ filters: { company: frm.doc.company, active: 1 } }),
			},
			{
				fieldname: "primary_technician",
				fieldtype: "Link",
				options: "Technician",
				label: __("Primary Technician"),
				default: frm.doc.primary_technician,
				get_query: () => ({ filters: { company: frm.doc.company, active: 1 } }),
			},
		],
		primary_action_label: __("Schedule and open visit"),
		primary_action: async (values) => {
			const { message } = await frappe.call({
				method: "fsm.process.guided.schedule_job_with_visit",
				args: { job: frm.doc.name, ...values },
				freeze: true,
			});
			dialog.hide();
			frappe.set_route("Form", "Service Visit", message.visit);
		},
	});
	dialog.show();
}

async function generate_report(frm) {
	const { message } = await frappe.call({
		method: "fsm.reporting.generate_service_report",
		args: { service_job: frm.doc.name },
		freeze: true,
	});
	frappe.set_route("Form", "Service Report", message.name);
}

async function create_invoice(frm) {
	const { message } = await frappe.call({
		method: "fsm.commercial.create_sales_invoice_from_job",
		args: { service_job: frm.doc.name },
		freeze: true,
	});
	frappe.set_route("Form", "Sales Invoice", message.name);
}

async function create_quotation(frm) {
	const { message } = await frappe.call({
		method: "fsm.commercial.create_quotation_from_job",
		args: { service_job: frm.doc.name },
		freeze: true,
	});
	frappe.set_route("Form", "Quotation", message.name);
}

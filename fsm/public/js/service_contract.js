frappe.ui.form.on("Service Contract", {
	setup(frm) {
		frm.set_query("customer_site", "covered_equipment", () => ({
			filters: {
				company: frm.doc.company || "",
				customer: frm.doc.customer || "",
				status: "Active",
			},
		}));
		frm.set_query("installed_equipment", "covered_equipment", () => ({
			filters: {
				company: frm.doc.company || "",
				customer: frm.doc.customer || "",
				customer_site: ["is", "set"],
				status: ["not in", ["Returned", "Replaced", "Disposed"]],
			},
		}));
	},
	refresh(frm) {
		if (frm.is_new()) {
			frm.set_intro(
				__("Define the customer, contract dates and covered sites or equipment first."),
				"blue",
			);
			return;
		}
		if (frm.doc.status === "Draft") {
			const commercialScopeReady =
				!frm.doc.automation_key || frm.doc.covered_equipment?.length;
			frm.set_intro(
				frm.doc.automation_key
					? __(
							"Review the sales source, equipment scope, service terms, and cadence. Activation will prepare draft maintenance plans automatically.",
						)
					: __("Review the scope and service terms before activation."),
				"orange",
			);
			if (commercialScopeReady) {
				frm.add_custom_button(
					__("Activate contract"),
					() => transition_contract(frm, "Active"),
					__("Next step"),
				);
			}
			if (frm.doc.automation_key && frm.doc.delivery_note) {
				frm.add_custom_button(
					__("Complete installation and contract scope"),
					() => open_after_sales(frm),
					__("Next step"),
				);
			}
		}
		if (frm.doc.status === "Active") {
			frm.add_custom_button(
				__("Create / open maintenance plans"),
				() => seed_plans(frm),
				__("Next step"),
			);
		}
		if (frm.doc.delivery_note) {
			frm.add_custom_button(
				__("Continue after-sales journey"),
				() => open_after_sales(frm),
				__("Next step"),
			);
		}
		frm.add_custom_button(
			__("View maintenance plans"),
			() => {
				frappe.set_route("List", "Maintenance Plan", { service_contract: frm.doc.name });
			},
			__("Related records"),
		);
	},
});

function open_after_sales(frm) {
	window.location.href = `/fsm-console/after-sales?delivery_note=${encodeURIComponent(frm.doc.delivery_note)}&contract=${encodeURIComponent(frm.doc.name)}`;
}

async function transition_contract(frm, status) {
	await frappe.call({
		method: "fsm.contracts.commands.transition_contract",
		args: { service_contract: frm.doc.name, status, source: "Console" },
		freeze: true,
	});
	await frm.reload_doc();
	if (status === "Active" && frm.doc.delivery_note) {
		window.location.href = `/fsm-console/after-sales?delivery_note=${encodeURIComponent(frm.doc.delivery_note)}&contract=${encodeURIComponent(frm.doc.name)}`;
	}
}

function seed_plans(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Create preventive maintenance plans"),
		fields: [
			{
				fieldname: "service_type",
				fieldtype: "Data",
				label: __("Service Type"),
				reqd: 1,
				default: __("Preventive Maintenance"),
			},
			{
				fieldname: "interval_count",
				fieldtype: "Int",
				label: __("Every"),
				reqd: 1,
				default: 3,
			},
			{
				fieldname: "interval_unit",
				fieldtype: "Select",
				label: __("Interval Unit"),
				reqd: 1,
				options: "Days\nWeeks\nMonths\nYears",
				default: "Months",
			},
			{
				fieldname: "first_due_date",
				fieldtype: "Date",
				label: __("First Due Date"),
				reqd: 1,
				default: frm.doc.start_date,
			},
			{
				fieldname: "timezone",
				fieldtype: "Data",
				label: __("Timezone"),
				reqd: 1,
				default: frappe.boot.time_zone?.system || "UTC",
			},
		],
		primary_action_label: __("Create and open plans"),
		primary_action: async (values) => {
			const { message } = await frappe.call({
				method: "fsm.process.maintenance_flow.create_maintenance_plans_from_contract",
				args: { service_contract: frm.doc.name, preview: 0, ...values },
				freeze: true,
			});
			dialog.hide();
			const first = message.plans?.[0]?.maintenance_plan;
			first
				? frappe.set_route("Form", "Maintenance Plan", first)
				: frappe.set_route("List", "Maintenance Plan", { service_contract: frm.doc.name });
		},
	});
	dialog.show();
}

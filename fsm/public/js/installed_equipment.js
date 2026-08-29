frappe.ui.form.on("Installed Equipment", {
	setup(frm) {
		frm.set_query("customer_site", () => ({
			filters: { customer: frm.doc.customer, company: frm.doc.company, enabled: 1 },
		}));
		frm.set_query("equipment_location", () => ({
			filters: { customer_site: frm.doc.customer_site, active: 1 },
		}));
	},
	refresh(frm) {
		if (frm.is_new()) return;
		if (frm.doc.status === "Pending Installation") {
			frm.set_intro(
				__(
					"Select the physical site and confirm installation before adding the equipment to a maintenance contract.",
				),
				"orange",
			);
			frm.add_custom_button(
				__("Confirm installation"),
				() => confirm_installation(frm),
				__("Next step"),
			);
		}
		frm.add_custom_button(
			__("Create Service Request"),
			() => {
				frappe.new_doc("Service Request", {
					company: frm.doc.company,
					customer: frm.doc.customer,
					customer_site: frm.doc.customer_site,
					installed_equipment: frm.doc.name,
				});
			},
			__("Service"),
		);
	},
});

function confirm_installation(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Confirm installation"),
		fields: [
			{
				fieldname: "customer_site",
				fieldtype: "Link",
				options: "Customer Site",
				label: __("Customer Site"),
				reqd: 1,
				default: frm.doc.customer_site,
				get_query: () => ({
					filters: { customer: frm.doc.customer, company: frm.doc.company, enabled: 1 },
				}),
			},
			{
				fieldname: "equipment_location",
				fieldtype: "Link",
				options: "Equipment Location",
				label: __("Equipment Location"),
				get_query: () => ({
					filters: { customer_site: dialog.get_value("customer_site"), active: 1 },
				}),
			},
			{
				fieldname: "installation_date",
				fieldtype: "Date",
				label: __("Installation Date"),
				reqd: 1,
				default: frappe.datetime.get_today(),
			},
			{ fieldname: "commissioning_date", fieldtype: "Date", label: __("Commissioning Date") },
		],
		primary_action_label: __("Confirm installation"),
		primary_action: async (values) => {
			await frappe.call({
				method: "fsm.installed_base.commands.confirm_installation",
				args: { installed_equipment: frm.doc.name, ...values },
				freeze: true,
			});
			dialog.hide();
			await frm.reload_doc();
		},
	});
	dialog.show();
}

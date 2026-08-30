frappe.ui.form.on("Delivery Note", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1 || frm.doc.is_return) return;
		const count = frm.doc.fsm_installed_equipment_count || 0;
		if (count) {
			frm.set_intro(
				__(
					"{0} equipment record(s) were created automatically. Continue the after-sales setup.",
					[count],
				),
				"green",
			);
			frm.add_custom_button(
				__("Continue after-sales setup"),
				() => {
					window.location.href = `/fsm-console/after-sales?delivery_note=${encodeURIComponent(frm.doc.name)}`;
				},
				__("Field Service"),
			);
			if (frm.doc.fsm_service_contract) {
				frm.add_custom_button(
					__("Review service contract"),
					() => frappe.set_route("Form", "Service Contract", frm.doc.fsm_service_contract),
					__("Field Service"),
				);
			}
			frm.add_custom_button(
				__("View installed equipment"),
				() => {
					frappe.set_route("List", "Installed Equipment", {
						delivery_note: frm.doc.name,
					});
				},
				__("Field Service"),
			);
		} else {
			frm.add_custom_button(
				__("Retry equipment provisioning"),
				async () => {
					await frappe.call({
						method: "fsm.installed_base.provisioning.reconcile_delivery_note_provisioning",
						args: { delivery_note: frm.doc.name },
						freeze: true,
					});
					await frm.reload_doc();
				},
				__("Field Service"),
			);
		}
	},
});

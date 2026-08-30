frappe.ui.form.on("Sales Invoice", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1 || frm.doc.is_return || frm.doc.fsm_service_job) return;
		if (frm.doc.fsm_service_contract) {
			frm.set_intro(
				__("A draft service contract was prepared automatically for after-sales review."),
				"green",
			);
			frm.add_custom_button(
				__("Review service contract"),
				() => frappe.set_route("Form", "Service Contract", frm.doc.fsm_service_contract),
				__("Field Service"),
			);
		}
	},
});

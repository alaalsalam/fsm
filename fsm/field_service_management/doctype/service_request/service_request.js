frappe.ui.form.on("Service Request", {
	refresh(frm) {
		if (["Open", "Triaged", "Converted"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Create Service Job"), () =>
				frappe.call("fsm.service_operations.commands.create_job_from_request", { request: frm.doc.name })
					.then((result) => frappe.set_route("Form", "Service Job", result.message.name)),
			);
		}
	},
});

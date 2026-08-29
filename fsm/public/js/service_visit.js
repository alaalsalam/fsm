frappe.ui.form.on("Service Visit", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(
			__("Open parent Service Job"),
			() => {
				frappe.set_route("Form", "Service Job", frm.doc.service_job);
			},
			__("Related records"),
		);
		if (frm.doc.status === "Planned") {
			frm.set_intro(
				frm.doc.primary_technician
					? __(
							"Dispatch the visit, then the technician continues travel, check-in and work from the field interface.",
						)
					: __("Assign a technician before dispatching this visit."),
				"orange",
			);
			if (frm.doc.primary_technician) {
				frm.add_custom_button(
					__("Dispatch visit"),
					() => dispatch_visit(frm),
					__("Next step"),
				);
			}
		} else if (!["Completed", "Cancelled"].includes(frm.doc.status)) {
			frm.set_intro(
				__("Continue field execution from the visits screen in the operations console."),
				"blue",
			);
			frm.add_custom_button(
				__("Open operations visits"),
				() => {
					window.location.href = "/fsm-console/visits";
				},
				__("Next step"),
			);
		}
	},
});

async function dispatch_visit(frm) {
	await frappe.call({
		method: "fsm.service_operations.commands.dispatch_visit",
		args: { visit: frm.doc.name, source: "Console" },
		freeze: true,
	});
	await frm.reload_doc();
}

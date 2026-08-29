frappe.ui.form.on("Maintenance Occurrence", {
	refresh(frm) {
		if (frm.is_new()) return;
		const releasable =
			["Forecast", "Due", "Overdue"].includes(frm.doc.status) &&
			frm.doc.auto_release_job &&
			frm.doc.release_on <= frappe.datetime.get_today();
		if (releasable) {
			frm.set_intro(
				__("Release this scheduled occurrence when it is ready for field execution."),
				"blue",
			);
			frm.add_custom_button(
				__("Create / open Service Job"),
				() => release_occurrence(frm),
				__("Next step"),
			);
		} else if (["Forecast", "Due", "Overdue"].includes(frm.doc.status)) {
			frm.set_intro(
				__("This occurrence will create its Service Job automatically on {0}.", [
					frappe.datetime.str_to_user(frm.doc.release_on),
				]),
				"blue",
			);
		}
		if (frm.doc.released_job) {
			frm.set_intro(
				__(
					"This occurrence is linked to a Service Job. Continue planning and execution there.",
				),
				"green",
			);
			frm.add_custom_button(
				__("Open linked Service Job"),
				() => frappe.set_route("Form", "Service Job", frm.doc.released_job),
				__("Next step"),
			);
		}
	},
});

async function release_occurrence(frm) {
	const { message } = await frappe.call({
		method: "fsm.maintenance.commands.release_plan_occurrences",
		args: { occurrence_names: [frm.doc.name] },
		freeze: true,
	});
	const job = message.jobs?.[0]?.name || message.jobs?.[0]?.job || message.jobs?.[0];
	if (job) frappe.set_route("Form", "Service Job", job);
	else await frm.reload_doc();
}

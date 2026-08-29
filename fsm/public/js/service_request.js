frappe.ui.form.on("Service Request", {
	setup(frm) {
		frm.set_query("customer_site", () => ({
			filters: { customer: frm.doc.customer, company: frm.doc.company, enabled: 1 },
		}));
		frm.set_query("installed_equipment", () => ({
			filters: {
				customer: frm.doc.customer,
				company: frm.doc.company,
				...(frm.doc.customer_site ? { customer_site: frm.doc.customer_site } : {}),
			},
		}));
	},
	refresh(frm) {
		if (frm.is_new()) {
			frm.set_intro(
				__(
					"Describe the request, select the customer and equipment, then save to start the guided workflow.",
				),
				"blue",
			);
			return;
		}
		const actions = {
			Draft: [__("Open service request"), "fsm.service_operations.commands.open_request"],
			Open: [__("Triage service request"), "fsm.service_operations.commands.triage_request"],
		};
		if (actions[frm.doc.status]) {
			const [label, method] = actions[frm.doc.status];
			frm.set_intro(label, "orange");
			frm.add_custom_button(label, () => run_request_action(frm, method), __("Next step"));
		}
		if (["Triaged", "Converted"].includes(frm.doc.status)) {
			frm.set_intro(
				__("Create or open the linked Service Job to continue planning and execution."),
				"blue",
			);
			frm.add_custom_button(
				__("Create / open Service Job"),
				() => open_request_job(frm),
				__("Next step"),
			);
		}
	},
	customer(frm) {
		if (!frm.doc.customer) frm.set_value({ customer_site: null, installed_equipment: null });
	},
	customer_site(frm) {
		if (!frm.doc.customer_site) return;
		frappe.db
			.get_value("Customer Site", frm.doc.customer_site, ["customer", "company"])
			.then(({ message }) => {
				if (message)
					frm.set_value({ customer: message.customer, company: message.company });
			});
	},
});

async function run_request_action(frm, method) {
	await frappe.call({ method, args: { request: frm.doc.name, source: "Console" }, freeze: true });
	await frm.reload_doc();
}

async function open_request_job(frm) {
	const { message } = await frappe.call({
		method: "fsm.service_operations.commands.create_job_from_request",
		args: { request: frm.doc.name, idempotency_key: `desk:${frm.doc.name}`, source: "Console" },
		freeze: true,
	});
	frappe.set_route("Form", "Service Job", message.name);
}

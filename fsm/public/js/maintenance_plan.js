// Maintenance Plan desk form — the Customer Site is the source of truth for
// ownership: picking a site auto-fills its Customer + Company (so the server's
// "Site must belong to the Customer and Company" guard can never trip from a
// stale company default), and every picker is filtered to consistent records.
frappe.ui.form.on("Maintenance Plan", {
	setup(frm) {
		frm.set_query("customer_site", () => {
			const filters = { status: "Active" };
			if (frm.doc.customer) filters.customer = frm.doc.customer;
			if (frm.doc.company) filters.company = frm.doc.company;
			return { filters };
		});
		frm.set_query("service_contract", () => {
			const filters = {};
			if (frm.doc.customer) filters.customer = frm.doc.customer;
			if (frm.doc.company) filters.company = frm.doc.company;
			return { filters };
		});
		frm.set_query("installed_equipment", "equipment", () => {
			const filters = {};
			if (frm.doc.customer_site) filters.customer_site = frm.doc.customer_site;
			else if (frm.doc.customer) filters.customer = frm.doc.customer;
			return { filters };
		});
	},

	customer_site(frm) {
		if (!frm.doc.customer_site) return;
		frappe.db
			.get_value("Customer Site", frm.doc.customer_site, ["customer", "company"])
			.then((response) => {
				const site = response?.message;
				if (!site) return;
				if (site.customer && site.customer !== frm.doc.customer) {
					frm.set_value("customer", site.customer);
				}
				if (site.company && site.company !== frm.doc.company) {
					frm.set_value("company", site.company);
				}
			})
			.catch(() => {
				frappe.msgprint(__("تعذّر جلب بيانات الموقع. أعد المحاولة."));
			});
	},

	customer(frm) {
		// A manually changed customer invalidates a site owned by someone else.
		if (!frm.doc.customer || !frm.doc.customer_site) return;
		frappe.db
			.get_value("Customer Site", frm.doc.customer_site, "customer")
			.then((response) => {
				const siteCustomer = response?.message?.customer;
				if (siteCustomer && siteCustomer !== frm.doc.customer) {
					frm.set_value("customer_site", null);
				}
			})
			.catch(() => {});
	},
});

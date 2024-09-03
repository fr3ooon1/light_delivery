// Copyright (c) 2024, Muhammad Essam and contributors
// For license information, please see license.txt

frappe.ui.form.on("Delivery", {
	delivery_location(frm) {
        console.log(frm.doc.delivery_location);
	},
});

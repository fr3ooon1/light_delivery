// Copyright (c) 2024, Muhammad Essam and contributors
// For license information, please see license.txt

frappe.ui.form.on("Store", {
	store_location(frm) {
        console.log(frm.doc.store_location);
	},
	refresh:function(frm){
		frm.set_query('order_type', 'order_type', () => {
			return {
				filters: {
					enable: 1
				}
			}
		})
	}
});

// Copyright (c) 2024, Muhammad Essam and contributors
// For license information, please see license.txt

frappe.ui.form.on("Order", {
	valuation:function(frm){
		console.log(frm.doc.valuation);
	},
	road_map:function(frm) {
        console.log(frm.doc.road_map)
	},
});

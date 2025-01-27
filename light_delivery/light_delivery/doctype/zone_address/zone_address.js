// Copyright (c) 2024, Muhammad Essam and contributors
// For license information, please see license.txt

frappe.ui.form.on("Zone Address", {
	refresh(frm) {

        if (frm.doc.geolocation_klnh) {
            console.log(frm.doc.geolocation_klnh);
            
            // let geolocation = frm.doc.geolocation_klnh.split(",");
            // frm.set_value("latitude", geolocation[0]);
            // frm.set_value("longitude", geolocation[1]);
        }

	},
    geolocation_klnh(frm) {

        if (frm.doc.geolocation_klnh) {
            console.log(frm.doc.geolocation_klnh);
            
            // let geolocation = frm.doc.geolocation_klnh.split(",");
            // frm.set_value("latitude", geolocation[0]);
            // frm.set_value("longitude", geolocation[1]);
        }

	},
});

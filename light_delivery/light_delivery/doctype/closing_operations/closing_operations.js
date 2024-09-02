// Copyright (c) 2024, Muhammad Essam and contributors
// For license information, please see license.txt

frappe.ui.form.on("Closing operations", {
	party_type:function(frm) {
        let party_type = frm.doc.party_type;
        if(party_type){
            frappe.call({
                method:"dynamic.api.get_customer_branches",
                args:{
                    "party_type":party_type
                },
                callback(r){
                    console.log(r.message)
                    if(r.message){
                        frm.set_value("amount" , r.message);
                        frm.refresh_field("amount");
                    }
                }
            })
        }
	},
});

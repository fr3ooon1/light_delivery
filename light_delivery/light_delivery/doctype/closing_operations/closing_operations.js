// Copyright (c) 2024, Muhammad Essam and contributors
// For license information, please see license.txt

frappe.ui.form.on("Closing operations", {
    refresh:function(frm){
        frm.add_custom_button(__("Create Invoice"), function () {
            frm.events.create_invoice(frm);
          });
    },
    create_invoice: function (frm) {
        if (!frm.doc.invoice_reference){
            frappe.call({
                method: "light_delivery.light_delivery.doctype.closing_operations.closing_operations.create_sales_invoice",
                args: {
                    doc: frm.doc.name,
                },
                callback: function () {
                    
                },
           });
        }else{
            msgprint("Invoice Already Created named: "+frm.doc.invoice_reference)
        }
      },
	party_type:function(frm) {
        let party_type = frm.doc.party_type;
        if(party_type){
            frappe.call({
                method:"light_delivery.api.delivery_request.calculate_balane",
                args:{
                    "party_type":party_type
                },
                callback(r){
                    if(r.message){
                        frm.set_value("amount" , r.message);
                        frm.refresh_field("amount");
                    }
                }
            })
        }
	},
});

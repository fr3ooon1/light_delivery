// Copyright (c) 2025, Muhammad Essam and contributors
// For license information, please see license.txt

frappe.ui.form.on("Notifications", {
	refresh:function(frm) {
        if (!frm.is_new()){
            frm.events.send_notification(frm);
        }
        frm.events.party_type(frm);
        frm.events.send_to(frm);
        
	},
    send_to:function(frm){
        if (frm.doc.send_to){

            


            frm.set_value("send_to_particular_segments",0)
            frm.refresh_field("send_to_particular_segments")
        }
    },
    send_to_particular_segments:function(frm){

        if (frm.doc.send_to_particular_segments){
            // frm.set_df_property("user","hidden",1)
            // frm.set_df_property("user","reqd",0)


            frm.set_df_property("zone_address","hidden",1)
            frm.set_df_property("delivery_category","hidden",1)

            frm.set_df_property("zone_address","reqd",0)
            frm.set_df_property("delivery_category","reqd",0)

            frm.set_value("send_to",0)
            frm.refresh_field("send_to")

            frm.set_value("party_type",undefined)
            frm.refresh_field("party_type")

            frm.set_value("zone_address",undefined)
            frm.refresh_field("zone_address")
            
        }
            
    },
    party_type:function(frm){
        if (frm.doc.party_type == "Customer" || frm.doc.party_type =="Store"){
            frm.set_df_property("zone_address","hidden",0)
            frm.set_df_property("delivery_category","hidden",1)

            frm.set_df_property("zone_address","reqd",1)
            frm.set_df_property("delivery_category","reqd",0)

        }else if(frm.doc.party_type == "Delivery"){
            frm.set_df_property("zone_address","hidden",1)
            frm.set_df_property("delivery_category","hidden",0)

            frm.set_df_property("zone_address","reqd",0)
            frm.set_df_property("delivery_category","reqd",1)
        }
    },
    send_notification:function(frm){
        frm.add_custom_button(__('Send Notification'), function() {
            frappe.call({
                method: "light_delivery.light_delivery.doctype.notifications.notifications.send_notification",
                args: {
                    doc: frm.doc.name
                },
            });
        });
    },
});

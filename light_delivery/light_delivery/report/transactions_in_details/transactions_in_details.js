// Copyright (c) 2024, Muhammad Essam and contributors
// For license information, please see license.txt

frappe.query_reports["Transactions in details"] = {
	"filters": [
        {
            "fieldname": "party",
            "label": __("Choose"),
            "fieldtype": "Select",
            "options": "Store\nDelivery",
            "default": "Store" ,
			on_change: () => {
				frappe.query_report.set_filter_value("party_type", ' ');
						frappe.query_report.refresh();
			},
		},
		{
			fieldname: "party_type",
			label: __("Party"),
			fieldtype: "Dynamic Link",
			"get_options": function() {
						var applicant_type = frappe.query_report.get_filter_value('party');
						var applicant = frappe.query_report.get_filter_value('party_type');
						if(applicant && !applicant_type) {
							frappe.throw(__("Please select Party Type first"));
						}
						return applicant_type;
			}
		},  
    ],
};

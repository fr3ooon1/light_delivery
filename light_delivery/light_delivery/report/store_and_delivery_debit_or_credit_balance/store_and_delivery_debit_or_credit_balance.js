// Copyright (c) 2024, Muhammad Essam and contributors
// For license information, please see license.txt

frappe.query_reports["Store and Delivery debit or credit balance"] = {
	"filters": [
        {
            "fieldname": "party",
            "label": __("Choose"),
            "fieldtype": "Select",
            "options": "Store\nDelivery",
            "default": "Store" 
        },
    ],

    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname === "net_balance") {
            let color = "black";
            
            
            value = `<span style="color: ${color}; font-weight: bold;">${value}</span>`;
        }   
        return value;
    }
};

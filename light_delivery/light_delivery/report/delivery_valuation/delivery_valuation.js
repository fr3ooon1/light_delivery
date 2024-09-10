// Copyright (c) 2024, Muhammad Essam and contributors
// For license information, please see license.txt

frappe.query_reports["Delivery Valuation"] = {
	"filters": [
        {
            "fieldname": "delivery_category",
            "label": __("Delivery Category"),
            "fieldtype": "Link",
            "options": "Delivery Category",
            "default": "",
            "reqd": 0
        },
        {
            "fieldname": "date_of_joining",
            "label": __("Date of Joining"),
            "fieldtype": "Date",
            "default": "",
            "reqd": 0
        },
		{
            "fieldname": "valuation",
            "label": __("Valuation"),
            "fieldtype": "Rating",
            "default": "",
            "reqd": 0
        },
    ],

	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		// Center the text in specific columns
		if (column.fieldname === "name" || 
			column.fieldname === "delivery_name" || 
			column.fieldname === "date_of_joining" || 
			column.fieldname === "delivery_category" || 
			column.fieldname === "valuation" ||
			column.fieldname === "total_delivered" || 
			column.fieldname === "total_canceled") {
			
			value = `<div style="text-align: center;">${value}</div>`;
		}

		return value;
	}

}

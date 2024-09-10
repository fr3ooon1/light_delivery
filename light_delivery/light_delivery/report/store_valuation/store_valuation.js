// Copyright (c) 2024, Muhammad Essam and contributors
// For license information, please see license.txt

frappe.query_reports["Store Valuation"] = {
	"filters": [
        {
            "fieldname": "store_name",
            "label": __("Store Name"),
            "fieldtype": "Link",
            "options": "Store",
            "default": "",
            "reqd": 0
        },
        {
            "fieldname": "status",
            "label": __("Status"),
            "fieldtype": "Select",
			"options": "\nPending\nActive\nInactive",
            "reqd": 0
        },
		{
            "fieldname": "zone",
            "label": __("Zone"),
            "fieldtype": "Link",
			"options": "Zone Address",
            "reqd": 0
        },
    ],

	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		// Center the text in specific columns
		if (column.fieldname === "name" || 
			column.fieldname === "store_name" || 
			column.fieldname === "status" || 
			column.fieldname === "store_category" || 
			column.fieldname === "minimum_price" ||
			column.fieldname === "rate_of_km" ||
			column.fieldname === "total_delivered" ||
			column.fieldname === "total_canceled") {
			
			value = `<div style="text-align: center;">${value}</div>`;
		}

		return value;
	}

}

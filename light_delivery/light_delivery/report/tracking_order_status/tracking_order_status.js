// Copyright (c) 2024, Muhammad Essam and contributors
// For license information, please see license.txt
 

frappe.query_reports["Tracking Order Status"] = {
    "filters": [
		{
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            "reqd": 0
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 0
        },
        {
            "fieldname": "status",
            "label": __("Status"),
            "fieldtype": "Select",
            "options": [
				{ "label": __("All"), "value": "" },
				{ "label": __("Pending"), "value": "Pending" },
				{ "label": __("On The Way"), "value": "On The Way" },
                { "label": __("Delivered"), "value": "Delivered" },
                { "label": __("Cancelled"), "value": "Cancel" }
            ],
            "default": "All",
        },
		{
            "fieldname": "order_type",
            "label": __("Order Type"),
            "fieldtype": "Link",
            "options": "Order Type",
            "reqd": 0
        },
        {
            "fieldname": "store",
            "label": __("Store"),
            "fieldtype": "Link",
            "options": "Store",
            "reqd": 0
        },
        {
            "fieldname": "delivery",
            "label": __("Delivery"),
            "fieldtype": "Link",
            "options": "Delivery",
            "reqd": 0
        }
    ],

	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		// Center the text in specific columns
		if (column.fieldname === "order_id" || 
			column.fieldname === "status" || 
			column.fieldname === "order_type" || 
			column.fieldname === "delivery_name" || 
			column.fieldname === "order_date" ||
			column.fieldname === "store_name" || 
			column.fieldname === "delivery_category" ||
			column.fieldname === "total_distance" ) {
			
			value = `<div style="text-align: center;">${value}</div>`;
		}

		if (column.fieldname === "status") {
			let color = "black"; 

			if (value.includes("Pending")) {
				color = "grey";
			} else if (value.includes("Delivered")) {
				color = "green";
			} else if (value.includes("On The Way")) {
				color = "orange";
			} else if (value.includes("Delivery Cancel") || value.includes("Store Cancel") || value.includes("Cancel")) {
				color = "red";
			}

			value = `<span style="color: ${color}; font-weight: bold;">${value}</span>`;
		}

		return value;
	}

};

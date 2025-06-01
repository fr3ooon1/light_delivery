// Copyright (c) 2025, Muhammad Essam and contributors
// For license information, please see license.txt

frappe.query_reports["Acc-Rej per Delivery"] = {
    filters: [
        {
            fieldname: "delivery",
            label: __("Delivery"),
            fieldtype: "Link",
            options: "Delivery",
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 1,
            default:
                frappe.defaults.get_user_default("year_start_date") ||
                frappe.datetime.month_start(),
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 1,
            default:
                frappe.defaults.get_user_default("year_end_date") || frappe.datetime.get_today(),
        },
    ],
};

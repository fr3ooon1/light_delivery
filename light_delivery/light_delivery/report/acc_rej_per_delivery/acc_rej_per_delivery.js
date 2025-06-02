// Copyright (c) 2025, Muhammad Essam and contributors
// For license information, please see license.txt

frappe.query_reports["Acc-Rej per Delivery"] = {
    onload: function (report) {
        report.page.add_inner_button("Reset Filters", function () {
            // Loop through filters and reset
            report.filters.forEach((filter) => {
                if (filter.fieldname === "delivery") {
                    filter.set_value("");
                }
                if (filter.fieldname === "from_date") {
                    filter.set_value(
                        frappe.defaults.get_user_default("year_start_date") ||
                            frappe.datetime.year_start()
                    );
                }
                if (filter.fieldname === "to_date") {
                    filter.set_value(
                        frappe.defaults.get_user_default("year_end_date") ||
                            frappe.datetime.get_today()
                    );
                }
            });

            // Refresh report with cleared filters
            listview.refresh();
            frappe.query_report.refresh();
        });
    },
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
                frappe.defaults.get_user_default("year_start_date") || frappe.datetime.year_start(),
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

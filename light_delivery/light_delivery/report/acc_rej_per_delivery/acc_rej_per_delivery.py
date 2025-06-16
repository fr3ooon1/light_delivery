# Copyright (c) 2025, Muhammad Essam and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate


def execute(filters=None):
    validate_filters(filters)
    data = get_data(filters)
    columns = get_columns()
    return columns, data


def validate_filters(filters):
    if not filters.from_date:
        filters.from_date = filters.year_start_date

    if not filters.to_date:
        filters.to_date = filters.year_end_date

    filters.from_date = getdate(filters.from_date)
    filters.to_date = getdate(filters.to_date)

    if filters.from_date > filters.to_date:
        frappe.throw(_("From Date cannot be greater than To Date"))


def get_data(filters):
    delivery_filter = ""
    values = [filters.from_date, filters.to_date]

    if filters.get("delivery"):
        delivery_filter = "AND log.delivery = %s"
        values.append(filters.delivery)

    query = f"""
        SELECT 
            log.delivery,
            COUNT(*) AS total_requests,
            COUNT(CASE WHEN log.status = 'Accepted' THEN 1 END) AS accepted_requests,
            COUNT(CASE WHEN log.status = 'Reject' THEN 1 END) AS rejected_requests,
            ROUND(COUNT(CASE WHEN log.status = 'Accepted' THEN 1 END) * 100.0 / COUNT(*), 2) AS accepted_percentage,
            ROUND(COUNT(CASE WHEN log.status = 'Reject' THEN 1 END) * 100.0 / COUNT(*), 2) AS rejected_percentage
        FROM 
            `tabLog` log
        INNER JOIN 
            `tabRequest Log` req ON log.parent = req.name
        WHERE 
            log.time BETWEEN %s AND %s
            {delivery_filter}
        GROUP BY 
            log.delivery
        ORDER BY 
            log.delivery ASC
    """

    result = frappe.db.sql(query, values, as_dict=True)
    for row in result:
        row.update({
            "total_requests_dis": row.total_requests,
            "accepted_requests_dis": row.accepted_requests,
            "rejected_requests_dis": row.rejected_requests,
            "accepted_percentage_dis": row.accepted_percentage,
            "rejected_percentage_dis": row.rejected_percentage
        })

    return result

def get_columns():
    return [
        {
            "fieldname": "delivery",
            "label": _("Delivery"),
            "fieldtype": "Link",
            "options": "Delivery",
            "width": 200,
        },
        {
            "fieldname": "total_requests",
            "label": _("Total Received Requests"),
            "fieldtype": "Int",
            "width": 178,
        },
        {
            "fieldname": "accepted_requests",
            "label": _("Accepted Requests"),
            "fieldtype": "Int",
            "width": 145,
        },
        {
            "fieldname": "rejected_requests",
            "label": _("Rejected Requests"),
            "fieldtype": "Int",
            "width": 140,
        },
        {
            "fieldname": "accepted_percentage",
            "label": _("Accepted Received (%)"),
            "fieldtype": "Percent",
            "width": 160,
        },
        {
            "fieldname": "rejected_percentage",
            "label": _("Rejected Received (%)"),
            "fieldtype": "Percent",
            "width": 160,
        },
        {
            "fieldname": "total_requests_dis",
            "label": _("Total Actual Requests"),
            "fieldtype": "Int",
            "width": 160,
        },
        {
            "fieldname": "accepted_requests_dis",
            "label": _("Accepted Actual Requests"),
            "fieldtype": "Int",
            "width": 200,
        },
        {
            "fieldname": "rejected_requests_dis",
            "label": _("Rejected Actual Requests"),
            "fieldtype": "Int",
            "width": 200,
        },
        {
            "fieldname": "accepted_percentage_dis",
            "label": _("Accepted Actual Requests (%)"),
            "fieldtype": "Percent",
            "width": 210,
        },
        {
            "fieldname": "rejected_percentage_dis",
            "label": _("Rejected Actual Request (%)"),
            "fieldtype": "Percent",
            "width": 200,
        },
    ] 



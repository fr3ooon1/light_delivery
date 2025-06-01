# Copyright (c) 2025, Muhammad Essam and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import getdate


def execute(filters=None):
    validate_filters(filters)
    data = get_data(filters)
    columns = get_columns()
    return columns, data


def validate_filters(filters):
    print("Validating filters:", filters)
    if not filters.from_date:
        filters.from_date = filters.year_start_date

    if not filters.to_date:
        filters.to_date = filters.year_end_date

    filters.from_date = getdate(filters.from_date)
    filters.to_date = getdate(filters.to_date)

    if filters.from_date > filters.to_date:
        frappe.throw(_("From Date cannot be greater than To Date"))



def get_data(filters):
    query = """
    SELECT 
        t1.delivery,
        COUNT( t1.parent ) AS total_requests,
        COUNT( CASE WHEN t1.status = 'Accepted' THEN t1.parent END) AS accepted_requests,
        COUNT( CASE WHEN t1.status = 'Reject' THEN t1.parent END) AS rejected_requests,
        COUNT( DISTINCT t1.parent ) AS total_requests_dis,
        ROUND(COUNT( CASE WHEN t1.status ='Accepted' THEN t1.delivery END)*100/COUNT(t1.delivery),2) AS accepted_percentage,
        ROUND(COUNT( CASE WHEN t1.status ='Reject' THEN t1.delivery END)*100/COUNT(t1.delivery),2) AS rejected_percentage,
            
        t2.accepted_requests_dis AS accepted_requests_dis,
        t2.rejected_requests_dis AS rejected_requests_dis,
        t2.accepted_percentage_dis AS accepted_percentage_dis,
        t2.rejected_percentage_dis AS rejected_percentage_dis
    FROM 
        tabLog AS t1
    JOIN (
        SELECT 
            delivery,
            COUNT( CASE WHEN status ='Accepted' THEN delivery END) AS accepted_requests_dis,
            COUNT( CASE WHEN status ='Reject' THEN delivery END) AS rejected_requests_dis,
            ROUND(COUNT( CASE WHEN status ='Accepted' THEN delivery END)*100/COUNT(delivery),2) AS accepted_percentage_dis,
            ROUND(COUNT( CASE WHEN status ='Reject' THEN delivery END)*100/COUNT(delivery),2) AS rejected_percentage_dis
        FROM 
            tabLog
        WHERE 
            parent IN ( SELECT request_delivery FROM `tabRequest Log` )
            AND (parent, delivery, time) IN ( SELECT parent, delivery, MAX(time) FROM tabLog GROUP BY parent, delivery )
        GROUP BY 
            delivery
    ) AS t2 ON t1.delivery = t2.delivery
    WHERE 
        parent 
            IN(
                SELECT
                    request_delivery 
                FROM 
                    `tabRequest Log`
            )
    """
    
    # Where clause
    filters_values = [filters.from_date, filters.to_date]
    if filters.delivery is not None:
        query += " AND t1.delivery = %s"
        filters_values.insert(0, filters.delivery)
    query += " AND t1.creation BETWEEN %s AND %s"
    query += """
    GROUP BY
        t1.delivery;
    """
    data = frappe.db.sql(query, filters_values, as_dict=True)
    return data





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

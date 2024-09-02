# Copyright (c) 2024, Muhammad Essam and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def get_delivery_report(filters=None):
    if not filters:
        filters = {}

    deliveries = frappe.get_all('Delivery',
        fields=['name', 'delivery_name', 'date_of_joining', 'delivery_category', 'valuation'],
        filters=filters
    )

    report_data = []
    
    for delivery in deliveries:
        delivery_name = delivery['name']
        
        request_data = frappe.db.sql("""
            SELECT
                SUM(CASE WHEN d_r.status = 'Delivered' THEN 1 ELSE 0 END) AS total_delivered,
                SUM(CASE WHEN d_r.status IN ('Delivery Cancel', 'Store Cancel', 'Cancel') THEN 1 ELSE 0 END) AS total_canceled
            FROM `tabRequest Delivery` as d_r
            WHERE delivery = %s
        """, delivery_name, as_dict=True)
        
        if request_data:
            delivery.update({
                'total_delivered': request_data[0].total_delivered,
                'total_canceled': request_data[0].total_canceled
            })

        report_data.append(delivery)

    return report_data

def get_report_columns():
    return [
        {"label": _("Delivery Name"), "fieldname": "name", "fieldtype": "Link", "options": "Delivery", "width": 180},
		{"label": _("Delivery Name"), "fieldname": "delivery_name", "fieldtype": "Data", "width": 180},
        {"label": _("Date of Joining"), "fieldname": "date_of_joining", "fieldtype": "Date", "width": 150},
        {"label": _("Delivery Category"), "fieldname": "delivery_category", "fieldtype": "Link", "options": "Delivery Category", "width": 180},
        {"label": _("Valuation"), "fieldname": "valuation", "fieldtype": "Rating", "width": 150},
        {"label": _("Total Requested Delivered"), "fieldname": "total_delivered", "fieldtype": "Int", "width": 150},
        {"label": _("Total Requested Canceled"), "fieldname": "total_canceled", "fieldtype": "Int", "width": 150}
    ]


def execute(filters=None):
    columns = get_report_columns()
    data = get_delivery_report(filters)
    return columns, data

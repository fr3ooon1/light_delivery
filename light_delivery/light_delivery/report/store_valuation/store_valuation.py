# Copyright (c) 2024, Muhammad Essam and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def get_store_report(filters=None):
    if not filters:
        filters = {}

    stores = frappe.get_all('Store',
        fields=['name', 'store_name', 'status','store_category','minimum_price','rate_of_km'],
        filters=filters
    )

    report_data = []
    
    for store in stores:
        store_name = store['name']
        
        request_data = frappe.db.sql("""
            SELECT
                SUM(CASE WHEN d_r.status = 'Delivered' THEN 1 ELSE 0 END) AS total_delivered,
                SUM(CASE WHEN d_r.status IN ('Delivery Cancel', 'Store Cancel', 'Cancel') THEN 1 ELSE 0 END) AS total_canceled
            FROM `tabRequest Delivery` as d_r
            WHERE store = %s
        """, store_name, as_dict=True)
        
        if request_data:
            store.update({
                'total_delivered': request_data[0].total_delivered,
                'total_canceled': request_data[0].total_canceled
            })

        report_data.append(store)

    return report_data

def get_report_columns():
    return [
        {"label": _("Store ID"), "fieldname": "name", "fieldtype": "Link", "options": "Store", "width": 150},
		{"label": _("Store Name"), "fieldname": "store_name", "fieldtype": "Data", "width": 150},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 150},
		{"label": _("Store Category"), "fieldname": "store_category", "fieldtype": "Link", "options": "Store Category", "width": 150},
        {"label": _("Minimum Price"), "fieldname": "minimum_price", "fieldtype": "Currency", "width": 140},
        {"label": _("Rate of km"), "fieldname": "rate_of_km", "fieldtype": "Currency", "width": 140},
        {"label": _("Total Requested Delivered"), "fieldname": "total_delivered", "fieldtype": "Int", "width": 120},
        {"label": _("Total Requested Canceled"), "fieldname": "total_canceled", "fieldtype": "Int", "width": 120}
    ]

def execute(filters=None):
	columns = get_report_columns()
	data = get_store_report(filters)
	return columns, data

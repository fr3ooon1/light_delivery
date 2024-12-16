# Copyright (c) 2024, Muhammad Essam and contributors
# For license information, please see license.txt


import frappe
from frappe import _


def execute(filters=None):
    conditions = "1=1"

    if filters.get("status") == "Cancel":
        conditions += " and o.status IN ('Delivery Cancel', 'Store Cancel', 'Cancel')"
    elif filters.get("status"):
        conditions += " and o.status = %(status)s"
    if filters.get("store"):
        conditions += " and o.store = %(store)s"
    if filters.get("delivery"):
        conditions += " and o.delivery = %(delivery)s"
    if filters.get("date_range"):
        conditions += " and o.order_date between %(from_date)s and %(to_date)s"
    if filters.get("order_type"):
        conditions += " and o.order_type = %(order_type)s"


    data = frappe.db.sql("""
        select
            o.name as order_id,
            o.status,
            o.order_date,
            d.delivery_category ,
            o.phone_number as customer_mobile,
			o.order_type,
            o.delivery,
            d.delivery_name,
            o.store,
            s.store_name,
            o.total_distance
        from
            `tabOrder` o
        left join
            `tabDelivery` d on o.delivery = d.name
        left join
            `tabStore` s on o.store = s.name
        where
            {conditions}
        order by
            o.creation desc
    """.format(conditions=conditions), filters, as_dict=1)

    if data:
        for i in data:
            
            i['store_mobile'] = frappe.get_value("User",{"username":i.get("store")},'mobile_no')
            i['delivery_mobile'] = frappe.get_value("User",{"username":i.get("delivery")},'mobile_no')

    columns = [
        {"label": "Order ID", "fieldname": "order_id", "fieldtype": "Link", "options": "Order", "width": 150},
        {"label": "Delivery Category", "fieldname": "delivery_category", "fieldtype": "Link", "options": "Delivery Category", "width": 150},
        {"label": "Order Type", "fieldname": "order_type", "fieldtype": "Data", "width": 150},
		{"label": "Status", "fieldname": "status", "fieldtype": "Select", "options": "Pending\nAccepted\nDelivered\nCancelled", "width": 150},
		{"label": "Order Date", "fieldname": "order_date", "fieldtype": "Date", "width": 150},
        {"label": "Delivery Person", "fieldname": "delivery_name", "fieldtype": "Link", "options": "Delivery", "width": 150},
        {"label": "Store", "fieldname": "store_name", "fieldtype": "Link", "options": "Store", "width": 150},
        {"label": "Total Distance", "fieldname": "total_distance", "fieldtype": "Float", "width": 150},

        {"label": "Customer Mobile", "fieldname": "customer_mobile", "fieldtype": "Data", "width": 150},
        {"label": "Store Mobile", "fieldname": "store_mobile", "fieldtype": "Data", "width": 150},
        {"label": "Delivery Mobile", "fieldname": "delivery_mobile", "fieldtype": "Data", "width": 150},

    ]
    
    summary = get_report_summary(data)

    return columns, data, None, None, summary

def get_report_summary(data):
    if not data:
        return None

    total_delivered = sum(1 for row in data if row.get("status") == "Delivered")
    total_cancelled = sum(1 for row in data if row.get("status") in ["Delivery Cancel", "Store Cancel", "Cancel"])
    total_on_way = sum(1 for row in data if row.get("status") == "On The Way")
    
    return[
        {
            'value' : total_delivered,
            'indicator' : 'Green',
            'label' : _('Total: Delivered'),
            'datatype' : 'Int',
        },
        {
            'value' : total_cancelled,
            'indicator' : 'Red',
            'label' :  _('Total: Cancelled'),
            'datatype' : 'Int',
        },
        {
            'value' : total_on_way,
            'indicator' : 'Orange',
            'label' : _('Total: On the way'),
            'datatype' : 'Int',
        },
    ]
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
    if not filters.from_date:
        filters.from_date = filters.year_start_date

    if not filters.to_date:
        filters.to_date = filters.year_end_date

    filters.from_date = getdate(filters.from_date)
    filters.to_date = getdate(filters.to_date)
    
    if filters.from_date > filters.to_date:
        frappe.throw(_("From Date cannot be greater than To Date"))



def get_data(filters):
    available_request_logs = frappe.get_all("Request Log", pluck='name')
    available_logs = frappe.get_all("Log", {"parent": ["IN", available_request_logs]}, pluck='parent')

    logs_filters = {
        "parent": ["IN", available_logs],
        "time": ["BETWEEN", [filters.from_date, filters.to_date]],
    }
    if filters.delivery:
        logs_filters["delivery"] = filters.delivery

    logs = frappe.get_all("Log",
        filters=logs_filters,
        fields=['name', 'parent', 'delivery', 'status', 'time'],
        order_by='time desc'
    )

    latest_by_pair, all_acc_requests, all_rej_requests, final_data = {}, [], [], []
    for log in logs:
        pair_key = (log.parent, log.delivery)
        if pair_key not in latest_by_pair:
            latest_by_pair[pair_key] = log

        if log.status == 'Accepted':
            all_acc_requests.append(log)
        elif log.status == 'Reject':
            all_rej_requests.append(log)

    latest_logs = list(latest_by_pair.values())
    
    acc_all = group_by_delivery(all_acc_requests)
    rej_all = group_by_delivery(all_rej_requests)
    latest_all = group_by_delivery(latest_logs)

    filters_values = []
    where_clauses = [
        "parent IN (SELECT request_delivery FROM `tabRequest Log`)",
        "(parent, delivery, time) IN (SELECT parent, delivery, MAX(time) FROM tabLog GROUP BY parent, delivery)"
    ]

    if filters.delivery:
        where_clauses.append("delivery = %s")
        filters_values.append(filters.delivery)

    where_clauses.append("creation BETWEEN %s AND %s")
    filters_values += [filters.from_date, filters.to_date]

    query = f"""
    SELECT 
        delivery,
        COUNT(CASE WHEN status = 'Accepted' THEN 1 END) AS accepted_requests_dis,
        COUNT(CASE WHEN status = 'Reject' THEN 1 END) AS rejected_requests_dis,
        ROUND(COUNT(CASE WHEN status = 'Accepted' THEN 1 END) * 100.0 / COUNT(*), 2) AS accepted_percentage_dis,
        ROUND(COUNT(CASE WHEN status = 'Reject' THEN 1 END) * 100.0 / COUNT(*), 2) AS rejected_percentage_dis
    FROM 
        tabLog
    WHERE 
        {" AND ".join(where_clauses)}
    GROUP BY
        delivery
    """

    query_data = frappe.db.sql(query, filters_values, as_dict=True)
    query_data_map = {row["delivery"]: row for row in query_data}
    all_deliveries = set(list(acc_all.keys()) + list(rej_all.keys()) + list(latest_all.keys()))
    
    for delivery in all_deliveries:
        total_requests = len(acc_all.get(delivery, [])) + len(rej_all.get(delivery, []))
        accepted_requests = len(acc_all.get(delivery, []))
        rejected_requests = len(rej_all.get(delivery, []))

        accepted_percentage = round((accepted_requests / total_requests) * 100, 2) if total_requests else 0
        rejected_percentage = round((rejected_requests / total_requests) * 100, 2) if total_requests else 0

        dis_row = query_data_map.get(delivery, {})
        total_requests_dis = dis_row.get("accepted_requests_dis", 0) + dis_row.get("rejected_requests_dis", 0)
        accepted_requests_dis = dis_row.get("accepted_requests_dis", 0)
        rejected_requests_dis = dis_row.get("rejected_requests_dis", 0)
        accepted_percentage_dis = dis_row.get("accepted_percentage_dis", 0.0)
        rejected_percentage_dis = dis_row.get("rejected_percentage_dis", 0.0)

        final_data.append({
            "delivery": delivery,
            "total_requests": total_requests,
            "accepted_requests": accepted_requests,
            "rejected_requests": rejected_requests,
            "accepted_percentage": accepted_percentage,
            "rejected_percentage": rejected_percentage,
            "total_requests_dis": total_requests_dis,
            "accepted_requests_dis": accepted_requests_dis,
            "rejected_requests_dis": rejected_requests_dis,
            "accepted_percentage_dis": accepted_percentage_dis,
            "rejected_percentage_dis": rejected_percentage_dis,
        })

    return final_data



def group_by_delivery(logs_list):
        grouped = {}
        for log in logs_list:
            delivery = log.delivery
            if delivery not in grouped:
                grouped[delivery] = []
            grouped[delivery].append(log)
        
        return grouped



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

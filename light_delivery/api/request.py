import frappe
from frappe import _
from frappe.utils import nowdate , get_first_day_of_week , get_first_day , getdate , get_site_base_path
from datetime import datetime
from light_delivery.api.apis import get_url
from light_delivery.api.apis import download_image


@frappe.whitelist(allow_guest=False)
def get_requests(*args, **kwargs):
    user = frappe.session.user
    store = frappe.get_value("Store", {"user": user}, 'name')
    requests = frappe.get_list("Request Delivery", 
                               {"store": store, 
                                'status': ['in', ['Accepted', 'Arrived', 'Collect Money', 'Picked', 'On The Way', 'Partially Delivered']]}, 
                               ['name as id', 'status', 'delivery', 'number_of_order', 'request_date'])

    for req in requests:
        request_del = frappe.get_doc("Request Delivery", req.get('id'))
        order_list = request_del.get("order_request")
        order_details = []

        for order in order_list:
            doc = frappe.get_doc("Order", order.order)
            res = {
                "id": doc.name,
                "total": doc.total_order,
                "date": doc.order_date,
                "customer": doc.full_name,
                "address": doc.address,
                "status": doc.status,
                
            }
            order_details.append(res)

        req['orders'] = order_details  # Append order details to the current request

    return requests
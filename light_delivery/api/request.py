import frappe
from frappe import _
from frappe.utils import nowdate , get_first_day_of_week , get_first_day , getdate , get_site_base_path
from datetime import datetime
from light_delivery.api.apis import get_url
from light_delivery.api.apis import download_image
import json


@frappe.whitelist(allow_guest=False)
def get_current_request(*args , **kwargs):
	user = frappe.session.user
	delivery = frappe.get_value("Delivery" ,{"user":user},'name')
	request = frappe.get_doc("Request Delivery",{"delivery":delivery , "status":["!=" , ""] })



@frappe.whitelist(allow_guest=False)
def request_history(*args, **kwargs):
	user = frappe.session.user
	delivery = frappe.get_value("Delivery", {"user": user}, 'name')

	if not delivery:
		return {"status": "error", "message": "No delivery found for the current user."}

	requests = frappe.get_list(
		"Request Delivery",
		filters={"delivery": delivery},
		fields=['name as id', 'number_of_order', 'number_ostoref_order', 'status', 'request_date', 'total as total_of_request']
	)
	for i in requests:
		i['orders'] = frappe.get_list(
			"Order Request",
			filters={"parent": i.get("id")},
			fields=['order']
		,ignore_permissions=True)

	return requests


@frappe.whitelist(allow_guest=False)
def delivery_request_status(*args , **kwargs):
	user = frappe.session.user
	delivery = frappe.get_value("Delivery", {"user": user}, ['name','delivery_category'],as_dict=1)
	res = {}
	
	if delivery:


		delivered = frappe.get_list("Request Delivery" , {"delivery":delivery.get("name") , "status":"Delivered"})
		accepted = frappe.get_list("Request Delivery" , {"delivery":delivery.get("name") , "status":"Accepted"})
		delivery_cancel = frappe.get_list("Request Delivery" , {"delivery":delivery.get("name") , "status":"Delivery Cancel"})
		store_cacnel = frappe.get_list("Request Delivery" , {"delivery":delivery.get("name") , "status":"Store Cancel"})


		price_list = frappe.get_value("Delivery Category" , delivery.get("delivery_category"), ['minimum_orders' , 'maximum_orders' , 'maximum_order_by_request' , 'minimum_rate' , 'rate_of_km'],as_dict=1)

		res = {
			"delivered":len(delivered),
			"accepted":len(accepted),
			"delivery_cancel":len(delivery_cancel),
			"store_cacnel":len(store_cacnel),
			"price_list":price_list
		}
		return res
	else:
		res = {
			"delivered":0,
			"accepted":0,
			"delivery_cancel":0,
			"store_cacnel":0,
			"price_list":0
		}
		return res


@frappe.whitelist(allow_guest=False)
def change_request_status(*args , **kwargs):
	status = kwargs.get("status")
	request = kwargs.get("request")
	try:
		if status and request:
			if frappe.db.exists("Request Delivery" , request):
				request_obj = frappe.get_doc("Request Delivery" , request)
				request_obj.status = status
				request_obj.save(ignore_permissions=True)
				frappe.db.commit()
				frappe.local.response['http_status_code'] = 200
				frappe.local.response['message'] = f""" Request id: {request} status has been changed"""
	except Exception as e:
		frappe.log_error(message=str(e), title=_('Error in change_request_status'))
		frappe.local.response['http_status_code'] = 500
		


@frappe.whitelist(allow_guest=False)
def get_requests(*args, **kwargs):
	user = frappe.session.user
	store = frappe.get_value("Store", {"user": user}, 'name')
	requests = frappe.get_list("Request Delivery", 
							   {"store": store, 
								'status': ['in', ['Accepted', 'Arrived', 'Collect Money', 'Picked', 'On The Way', 'Partially Delivered']]}, 
							   ['name as id', 'status', 'delivery', 'number_of_order', 'request_date','total'])

	for req in requests:
		request_del = frappe.get_doc("Request Delivery", req.get('id'))
		order_list = request_del.get("order_request")
		order_details = []

		for order in order_list:
			doc = frappe.get_doc("Order", order.order)
			if doc.status not in ['Delivery Cancel','Store Cancel']:
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



@frappe.whitelist(allow_guest=False)
def cancel_request(*args,**kwargs):
	request = kwargs.get("request")
	if frappe.db.exists("Request Delivery" , request):
		request_obj = frappe.get_doc("Request Delivery" , kwargs.get("request"))
		if kwargs.get("type") == 'store':
			request_obj.status = "Store Cancel"
			msg = f"""Request had been cancel by Store"""

		if kwargs.get("type") == 'delivery':
			request_obj.status = "Delivery Cancel"
			msg = f"""Request had been cancel by Store"""

		request_obj.save(ignore_permissions=True)
		frappe.db.commit()
		frappe.local.response['http_status_code'] = 200
		frappe.local.response['message'] = _(msg)
	else:
		frappe.local.response['http_status_code'] = 300
		frappe.local.response['message'] = _(f"""no request like {request}""")


@frappe.whitelist(allow_guest=False)
def change_delivery_status(*args, **kwargs):

	delivery = frappe.db.exists("Delivery", {"user": frappe.session.user})
	if not delivery:
		frappe.local.response['http_status_code'] = 404
		frappe.local.response['message'] = _("No delivery found for the current user.")
		return

	delivery = frappe.get_doc("Delivery", {"user": frappe.session.user})
	new_status = kwargs.get("status")

	if delivery.status == "Inorder":
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = _("Cannot change status while processing a delivery order.")
		return

	if new_status == "Online" and delivery.status == "Offline":
		delivery.status = "Avaliable"
		delivery.cash = float(kwargs.get("cash", 0))
		delivery.save(ignore_permissions=True)
		frappe.db.commit()
		frappe.local.response['http_status_code'] = 200
		frappe.local.response['message'] = _("The delivery status has been changed to Available.")

	elif new_status == "Offline" and delivery.status == "Avaliable":
		delivery.status = "Offline"
		delivery.save(ignore_permissions=True)
		frappe.db.commit()
		frappe.local.response['http_status_code'] = 200
		frappe.local.response['message'] = _("The delivery status has been changed to Offline.")

	else:
		frappe.local.response['http_status_code'] = 200
		frappe.local.response['message'] = _("The Delivery is already in this status.")

@frappe.whitelist(allow_guest=True)
def get_request_details_for_del(*args, **kwargs):

	delivery = frappe.get_value("Delivery", {"user": frappe.session.user}, 'name')
	
	if not delivery:
		frappe.local.response['http_status_code'] = 300
		frappe.local.response['message'] = _("No delivery found for the current user.")	

	request = frappe.get_all("Request Delivery", 
		filters={
			"delivery": delivery,
			"status": ["not in", ['Pending', 'Time Out', 'Delivery Cancel', 'Delivered', 'Store Cancel', 'Cancel']]
		},
		fields=["name", "number_of_order", "total", "store"],
		limit=1
	)
	if request:
		request_name = request[0].get("name")
		store = request[0].get("store")
		if store:

			coordi = frappe.get_doc("Store" , request[0].get("store")).store_location

			request[0]['coordi'] = json.loads(coordi).get("features")[0].get("geometry").get("coordinates" , None) 
		
		order = frappe.db.sql(f"""
			SELECT o.name, o.full_name, o.order_type, o.address, o.zone_address, o.invoice, o.total_order
			FROM `tabOrder` as o
			JOIN `tabRequest Delivery` as rd ON rd.name = '{request_name}'
			JOIN `tabOrder Request` as orq ON orq.parent = rd.name AND orq.order = o.name
			WHERE rd.name = '{request_name}';
		""", as_dict=1)


			
		
		request[0]['order'] = order
	
		frappe.local.response['http_status_code'] = 200
		return request[0] if request else {"message": "No valid request found."}
	else:
		frappe.local.response['http_status_code'] = 300
		frappe.local.response['message'] = _("No request for this delivery.")	


		
		



import frappe
from frappe import _
from frappe.utils import nowdate , get_first_day_of_week , get_first_day , getdate , get_site_base_path
from datetime import datetime
from light_delivery.api.apis import get_url
from light_delivery.api.apis import download_image
import json
from light_delivery.api.apis import send_notification 
from light_delivery.api.delivery_request import calculate_balane


@frappe.whitelist(allow_guest=False)
def get_current_request(*args , **kwargs):
	delivery = frappe.get_value("Delivery", {"user": frappe.session.user}, 'name')
	
	if not delivery:
		frappe.local.response['http_status_code'] = 300
		frappe.local.response['message'] = _("No delivery found for the current user.")	

	request = frappe.get_all("Request", 
		filters={
			"delivery": delivery,
			"status":'Waiting for delivery'
		},
		fields=["name", "number_of_order", "cash as total", "store" , "status" ,],
		limit=1
	)
	if not request:
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = _("No request for this delivery.")	
		return _("No request for this delivery.")	
	return request


@frappe.whitelist(allow_guest=False)
def request_history(*args, **kwargs):
	delivery = frappe.get_value("Delivery", {"user": frappe.session.user}, 'name')

	if not delivery:
		return {"status": "error", "message": "No delivery found for the current user."}

	requests = frappe.get_list(
		"Request Delivery",
		filters={"delivery": delivery},
		fields=['name as id', 'status', 'store', 'number_of_order', 'request_date','total']
	)
	for req in requests:
		request_del = frappe.get_doc("Request Delivery", req.get('id'))
		order_list = request_del.get("order_request")
		order_details = []

		for order in order_list:
			res = frappe.get_value("Order", order.get("order") , ['name','total_order','order_date','full_name','address','status','order_date'],as_dict=1)
			# res = {
			# 	"id": doc.name,
			# 	"total": doc.total_order,
			# 	"date": doc.order_date,
			# 	"customer": doc.full_name,
			# 	"address": doc.address,
			# 	"status": doc.status,	
			# }
			order_details.append(res)

		req['orders'] = order_details  # Append order details to the current request

	if not requests:
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = _("No requests for this delivery.")	
		return _("No requests for this delivery.")	
	return requests


@frappe.whitelist(allow_guest=False)
def delivery_request_status(*args , **kwargs):
	delivery = frappe.get_value("Delivery", {"user": frappe.session.user}, ['name','delivery_category','status','cash'],as_dict=1)
	res = {}
	wallet = calculate_balane(delivery.get("name")) if delivery else 0
	
	if delivery:


		delivered = frappe.get_list("Request Delivery" , {"delivery":delivery.get("name") , "status":"Delivered"})
		accepted = frappe.get_list("Request Delivery" , {"delivery":delivery.get("name") , "status":"Accepted"})
		delivery_cancel = frappe.get_list("Request Delivery" , {"delivery":delivery.get("name") , "status":"Delivery Cancel"})
		store_cacnel = frappe.get_list("Request Delivery" , {"delivery":delivery.get("name") , "status":"Store Cancel"})

		delivery_status = delivery.get("status")


		price_list = frappe.get_value("Delivery Category" , delivery.get("delivery_category"), ['minimum_orders' , 'maximum_orders' , 'maximum_order_by_request' , 'minimum_rate' , 'rate_of_km'],as_dict=1)

		res = {
			"delivered":len(delivered),
			"accepted":len(accepted),
			"delivery_cancel":len(delivery_cancel),
			"store_cacnel":len(store_cacnel),
			"price_list":price_list,
			"delivery_status":delivery_status,
			"wallet":float(wallet or 0),
			"cash": delivery.get("cash" or 0)
		}
		return res
	else:
		res = {
			"delivered":0,
			"accepted":0,
			"delivery_cancel":0,
			"store_cacnel":0,
			"price_list":0,
			"delivery_status":delivery.get("status"),
			"wallet":float(wallet or 0),
			"cash": delivery.get("cash" or 0)
		}
		return res


@frappe.whitelist(allow_guest=False)
def change_request_status(*args , **kwargs):
	status = kwargs.get("status")
	request = kwargs.get("request")
	notification_key=None
	try:
		if status and request:
			if frappe.db.exists("Request Delivery" , request):
				request_obj = frappe.get_doc("Request Delivery" , request)
				request_obj.status = status
				request_obj.save(ignore_permissions=True)
				frappe.db.commit()

				if frappe.db.exists("Delivery",{"user":frappe.session.user}):
					if request_obj.store:
						user = frappe.get_value("Store", request_obj.store , 'user')
						notification_key = frappe.get_value("User",user,'notification_key')
				else:
					if request_obj.delivery:
						user = frappe.get_value("Delivery", request_obj.delivery , 'user')
						notification_key = frappe.get_value("User",user,'notification_key')


				res = send_notification(notification_key, "modification")
				if res.status_code != 200:
					error = frappe.new_doc("Error Log")
					error.method = "send_notification"
					error.error = res.text
					error.insert(ignore_permissions=True)
				frappe.local.response['http_status_code'] = 200
				frappe.local.response['message'] = f""" Request id: {request} status has been changed"""
	except Exception as e:
		frappe.log_error(message=str(e), title=_('Error in change_request_status'))
		frappe.local.response['http_status_code'] = 400
		


@frappe.whitelist(allow_guest=False)
def get_requests(*args, **kwargs):
	user = frappe.session.user
	store = frappe.get_value("Store", {"user": user}, 'name')
	requests = frappe.get_list("Request Delivery", 
							   {"store": store, 
								'status': ['in', ['Accepted', 'Arrived', 'Collect Money', 'Picked', 'On The Way', 'Partially Delivered','Waiting for delivery']]}, 
							   ['name as id', 'status', 'delivery', 'number_of_order', 'request_date','total'])

	for req in requests:
		request_del = frappe.get_doc("Request Delivery", req.get('id'))
		order_list = request_del.get("order_request")
		order_details = []

		for order in order_list:
			doc = frappe.get_doc("Order", order.order)
			if doc.status not in ['Delivery Cancel','Store Cancel' , 'Cancel']:
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
	if not requests:
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = _("No requests for this store.")	
		return _("No requests for this store.")	
	return requests


@frappe.whitelist(allow_guest=False)
def cancel_request(*args,**kwargs):
	request = kwargs.get("request")
	notification_key = None
	if frappe.db.exists("Request Delivery" , request):
		request_obj = frappe.get_doc("Request Delivery" , kwargs.get("request"))
		if kwargs.get("type") == 'store':
			request_obj.status = "Store Cancel"
			msg = f"""Request had been cancel by Store"""

			delivery = frappe.get_value("Delivery",request_obj.delivery,"user")
			notification_key = frappe.get_value("User",delivery,'notification_key')
		
			

		if kwargs.get("type") == 'delivery':
			request_obj.status = "Delivery Cancel"
			msg = f"""Request had been cancel by Store"""

			store = frappe.get_value("Store",request_obj.store,"user")
			notification_key = frappe.get_value("User",store,'notification_key')

		res = send_notification(notification_key, "modification")
		if res.status_code != 200:
			error = frappe.new_doc("Error Log")
			error.method = "send_notification"
			error.error = res.text
			error.insert(ignore_permissions=True)

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
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = _("No delivery found for the current user.")
		return

	delivery = frappe.get_doc("Delivery", {"user": frappe.session.user})
	new_status = kwargs.get("status")

	if delivery.status == "Inorder":
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = _("Cannot change status while processing a delivery order.")
		return

	if new_status == "Online" and delivery.status in ["Offline","Hold"]:
		delivery.status = "Avaliable"
		delivery.cash = float(kwargs.get("cash", 0))
		delivery.save(ignore_permissions=True)
		frappe.db.commit()
		frappe.local.response['http_status_code'] = 200
		frappe.local.response['message'] = _("The delivery status has been changed to Available.")
		return {
			"message": _("The delivery status has been changed to Available."),
			"cash": float(kwargs.get("cash", 0))
		}

	elif new_status == "Offline" and delivery.status == "Avaliable":
		delivery.status = "Offline"
		delivery.save(ignore_permissions=True)
		frappe.db.commit()
		frappe.local.response['http_status_code'] = 200
		frappe.local.response['message'] = _("The delivery status has been changed to Offline.")

	else:
		frappe.local.response['http_status_code'] = 400
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
			"status": ["not in", ['Pending', 'Time Out', 'Delivery Cancel', 'Delivered', 'Store Cancel', 'Cancel' , 'Waiting for delivery']]
		},
		fields=["name", "number_of_order", "total", "store" , "status" ,"delivery"],
		limit=1
	)
	if request:

		balance =  float(calculate_balane(request[0].get("delivery")) or 0)
		request[0]['balance'] = balance
		tot = balance - request[0]['total']
		request[0]['cash'] = abs(tot)

		request_name = request[0].get("name")
		store = request[0].get("store")
		if store:

			store = frappe.get_doc("Store" , request[0].get("store"))

			request[0]['coordi'] = json.loads(store.store_location).get("features")[0].get("geometry").get("coordinates" , None) 
			request[0]['phone_number'] = frappe.get_value("User" , store.user , 'mobile_no')
			request[0]['address'] = store.address



		
		order = frappe.db.sql(f"""
			SELECT o.name, o.full_name, o.order_type, o.address, o.zone_address, o.invoice, o.total_order , o.phone_number , o.status
			FROM `tabOrder` as o
			JOIN `tabRequest Delivery` as rd ON rd.name = '{request_name}'
			JOIN `tabOrder Request` as orq ON orq.parent = rd.name AND orq.order = o.name
			WHERE rd.name = '{request_name}'
			AND o.status NOT IN ('Pending','Store Cancel','Delivered','Delivery Cancel','Cancel') ;
		""", as_dict=1)
		
		for i in order:

			images_of_orders = frappe.get_list(
										'Order Image',
										filters={'parent': i.get('name')},
										fields=['image'],
										pluck='image',
										ignore_permissions=True
									)

			i['images_of_orders'] = images_of_orders
			
		
		request[0]['order'] = order
	
		frappe.local.response['http_status_code'] = 200
		return request[0] if request else {"message": "No valid request found."}
	else:
		frappe.local.response['http_status_code'] = 300
		frappe.local.response['message'] = _("No request for this delivery.")	


		
		



import frappe
from frappe import _
from frappe.utils import nowdate , get_first_day_of_week , get_first_day , getdate , get_site_base_path
from datetime import datetime
from light_delivery.api.apis import get_url
from light_delivery.api.apis import download_image
import json
from light_delivery.api.apis import send_notification 
from light_delivery.api.delivery_request import get_balance
from light_delivery.api.apis import search_delivary  



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
		fields=['name as id', 'status', 'store', 'number_of_order', 'request_date','total','valuation'],
		ignore_permissions=True
	)
	for req in requests:
		request_del = frappe.get_doc("Request Delivery", req.get('id'))
		order_list = request_del.get("order_request")
		order_details = []
		req['valuation'] = float(float(request_del.valuation or 0) * 5 )

		for order in order_list:
			res = frappe.get_value(
				"Order", 
				order.get("order") , 
				[
					'name',
					'total_order',
					'order_date',
					'full_name',
					'address',
					'status',
					'order_date',
					'duration',
					'total_distance',
					'net_delivery_fees',
				],
				as_dict=1)

			order_details.append(res)

		req['orders'] = order_details  # Append order details to the current request

	if not requests:
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = _("No requests for this delivery.")	
		return _("No requests for this delivery.")	
	return requests


@frappe.whitelist(allow_guest=False)
def delivery_request_status(*args , **kwargs):
	delivery = frappe.get_value("Delivery", {"user": frappe.session.user}, ['name','delivery_category','status','cash','delivery_name'],as_dict=1)
	res = {}
	wallet = get_balance(delivery.get("delivery_name")) if delivery else 0
	
	if delivery:


		delivered = frappe.get_list("Order" , {"delivery":delivery.get("name") , "status":["IN",["Delivered","Return to store"]]})
		accepted = frappe.get_list("Order" , {"delivery":delivery.get("name") , "status":"Accepted"})
		delivery_cancel = frappe.get_list("Order" , {"delivery":delivery.get("name") , "status":"Cancel", "cancel_from":"Store"})
		store_cacnel = frappe.get_list("Order" , {"delivery":delivery.get("name") , "status":"Cancel" , "cancel_from":"Store"})


		status = None
		delivery_status = delivery.get("status")
		if delivery_status in ['Hold','Offline','Pending']:
			status = "Offline"
		else:
			status = "Online"


		price_list = frappe.get_value("Delivery Category" , delivery.get("delivery_category"), ['minimum_orders' , 'maximum_orders' , 'maximum_order_by_request' , 'minimum_rate' , 'rate_of_km'],as_dict=1)

		res = {
			"delivered":len(delivered),
			"accepted":len(accepted),
			"delivery_cancel":len(delivery_cancel),
			"store_cacnel":len(store_cacnel),
			"price_list":price_list,
			"delivery_status":status,
			"wallet":float(wallet or 0),
			"cash": float(delivery.get("cash" or 0) or 0)
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
def change_request_status(*args, **kwargs):
	"""
	Change the status of a Request Delivery and send a notification to the appropriate user.
	
	Args:
		*args: Additional positional arguments (not used).
		**kwargs: Dictionary containing:
			- status (str): New status for the request.
			- request (str): ID of the Request Delivery to be updated.

	Response:
		- HTTP status 200 on success with a message.
		- HTTP status 400 on failure with an error log.
	"""

	status = kwargs.get("status")
	request_id = kwargs.get("request")

	# Ensure response defaults
	frappe.local.response['http_status_code'] = 400

	if not (status and request_id):
		frappe.local.response['message'] = "Status and Request ID are required."
		return

	try:
		# Check if "Request Delivery" exists
		if not frappe.db.exists("Request Delivery", request_id):
			frappe.local.response['message'] = f"Request Delivery with ID {request_id} does not exist."
			return

		# Update the status
		request_obj = frappe.get_doc("Request Delivery", request_id)
		request_obj.status = status
		request_obj.save(ignore_permissions=True)
		frappe.db.commit()

		# Determine notification key
		notification_key = None
		user = None
		if frappe.db.exists("Delivery", {"user": frappe.session.user}):
			if request_obj.store:
				user = frappe.get_value("Store", request_obj.store, "user")
		else:
			if request_obj.delivery:
				user = frappe.get_value("Delivery", request_obj.delivery, "user")

		if user:
			notification_key = frappe.get_value("User", user, "notification_key")

		# Send notification if notification key exists
		if notification_key:
			res = send_notification(notification_key, "modification")
			if res.status_code != 200:
				frappe.log_error(
					message=f"Notification failed: {res.text}",
					title="Error in send_notification"
				)

		# Success response
		frappe.local.response['http_status_code'] = 200
		frappe.local.response['message'] = f"Request ID {request_id} status has been changed to {status}."
	except Exception as e:
		# Log any unhandled exceptions
		frappe.log_error(message=str(e), title="Error in change_request_status")
		frappe.local.response['message'] = f"An error occurred: {str(e)}"



@frappe.whitelist(allow_guest=False)
def get_requests(*args, **kwargs):
	user = frappe.session.user
	store = frappe.get_value("Store", {"user": user}, 'name')
	requests = frappe.get_list("Request Delivery", 
							   {"store": store, 
								'status': ['in', ['Accepted', 'Arrived', 'Collect Money', 'Picked', 'On The Way', 'Partially Delivered','Waiting for delivery']]}, 
							   ['name as id', 'status', 'delivery', 'number_of_order', 'request_date','total'])

	for req in requests:
		req['delivery_mobile'] = frappe.get_value("User",{"username",req.get("delivery")},"mobile_no")
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
					"invoice":doc.invoice,
					"customer_mobile": doc.phone_number,
				}
				order_details.append(res)

		req['orders'] = order_details  # Append order details to the current request
		req['cash'] = 0
		req['balance'] = 0
		if request_del.delivery:
			req['cash'] = frappe.get_value("Delivery",request_del.delivery,'cash')
			req['balance'] = get_balance(frappe.get_value("Delivery",request_del.delivery,'delivery_name')) 
	if not requests:
		frappe.local.response['http_status_code'] = 400
		# frappe.local.response['message'] = _("No requests for this store.")	
	return requests


@frappe.whitelist(allow_guest=False)
def cancel_request(*args, **kwargs):
	request_id = kwargs.get("request")
	cancel_type = kwargs.get("type")
	notification_key = None

	# Validate input
	if not request_id or not cancel_type:
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = _("Request ID and type are required.")
		return

	if not frappe.db.exists("Request Delivery", request_id):
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = _(f"No request found with ID: {request_id}")
		return

	try:
		request_obj = frappe.get_doc("Request Delivery", request_id)
		request_search_obj = frappe.get_doc("Request", request_id)

		# Determine the type of cancellation
		if cancel_type == "store":
			frappe.db.set_value("Request", request_id ,{
				"status": "Store Cancel",
				})
			cancel_orders(request_obj, "Store")
			msg = _("Request has been canceled by Store.")
			delivery_user = frappe.get_value("Delivery", request_obj.delivery, "user")
			notification_key = frappe.get_value("User", delivery_user, "notification_key")
			frappe.db.commit()

		elif cancel_type == "delivery":
			# frappe.db.set_value("Request", request_id ,{"status": "Waiting for Delivery"})
			# frappe.db.commit()
			request_search_obj.status = "Waiting for Delivery"

			frappe.db.set_value("Request Delivery", request_id ,{
				"status": "Waiting for Delivery",
				"delivery": None
				})
			frappe.db.commit()

			msg = _("Request has been canceled by Delivery.")
			store_user = frappe.get_value("Store", request_obj.store, "user")
			notification_key = frappe.get_value("User", store_user, "notification_key")
		else:
			frappe.local.response['http_status_code'] = 400
			frappe.local.response['message'] = _("Invalid cancellation type.")
			return

		# Send notification
		if notification_key:
			res = send_notification(notification_key, "modification")
			if res.status_code != 200:
				frappe.log_error(
					message=res.text, 
					title=_("Error sending notification")
				)

		request_search_obj.db_update()
		
		delivery_user = frappe.db.set_value("Delivery", request_obj.delivery, "status", "Avaliable")
		frappe.db.commit()
		frappe.local.response['http_status_code'] = 200
		frappe.local.response['message'] = msg

	except Exception as e:
		# Log unexpected errors and respond with error message
		frappe.log_error(message=str(e), title=_("Error in cancel_request"))
		frappe.local.response['http_status_code'] = 500
		frappe.local.response['message'] = _("An error occurred while canceling the request.")


def create_new_request(docname):
	doc = frappe.get_doc("Request Delivery", docname)
	obj = frappe.new_doc("Request Delivery")
	obj.number_of_order = doc.number_of_order
	obj.store = doc.store
	obj.status = "Pending"
	obj.request_date = nowdate()
	obj.total = doc.total

	for i in doc.order_request:
		obj.append("order_request", {
			"order": i.order,		
		})	
	obj.insert()

	frappe.db.commit()

def cancel_orders(request_obj, cancel_from):
	"""
	Helper function to cancel all orders in a request.
	"""
	orders = request_obj.get("order_request")
	for order in orders:
		order_doc = frappe.get_doc("Order", order.order)
		order_doc.status = "Cancel"
		order_doc.cancel_from = cancel_from
		order_doc.save(ignore_permissions=True)


@frappe.whitelist(allow_guest=False)
def change_delivery_status(*args, **kwargs):

	delivery = frappe.db.exists("Delivery", {"user": frappe.session.user})
	if not delivery:
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = _("No delivery found for the current user.")
		return _("No delivery found for the current user.")

	delivery = frappe.get_doc("Delivery", {"user": frappe.session.user})
	new_status = kwargs.get("status")

	if delivery.status == "Inorder":
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = _("Cannot change status while processing a delivery order.")
		return _("Cannot change status while processing a delivery order.")

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

	elif new_status == "Offline" and delivery.status in ["Avaliable","Hold","Offline"]:
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
		delivery_name = frappe.get_value("Delivery",request[0].get("delivery"),'delivery_name')
		balance =  float(get_balance(delivery_name or 0))
		request[0]['balance'] = balance
		tot = balance - request[0]['total']
		request[0]['cash'] = abs(tot)

		request_name = request[0].get("name")
		store = request[0].get("store")
		if store:

			store = frappe.get_doc("Store" , request[0].get("store"))

			# request[0]['coordi'] = [float(store.pointer_y) , float(store.pointer_x)]
			request[0]['coordi'] = json.loads(store.store_location).get("features")[0].get("geometry").get("coordinates" , None) 
			request[0]['phone_number'] = frappe.get_value("User" , store.user , 'mobile_no')
			request[0]['address'] = store.address



		
		order = frappe.db.sql(f"""
			SELECT o.name, o.full_name, o.order_type, o.address, o.zone_address, o.invoice, o.total_order , o.phone_number , o.status
			FROM `tabOrder` as o
			JOIN `tabRequest Delivery` as rd ON rd.name = '{request_name}'
			JOIN `tabOrder Request` as orq ON orq.parent = rd.name AND orq.order = o.name
			WHERE rd.name = '{request_name}'
			AND o.status NOT IN ('Pending','Store Cancel','Delivered','Delivery Cancel','Cancel','Return to store') ;
		""", as_dict=1)
		
		for i in order:

			images_of_orders = frappe.get_list(
										'Order Image',
										filters={'parent': i.get('name')},
										fields=['image'],
										pluck='image',
										ignore_permissions=True
									)
			i['coordi'] = [None,None]
			username = frappe.get_value("User",{"mobile_no":i.get("phone_number")},['username'],as_dict=1)

			if username:
				coordi = frappe.get_value("Address" , {"address_line1":i.get("address")} ,[ "latitude" , "longitude"] , as_dict = True) 
				if coordi:
					i['coordi'] = [float(coordi.get("latitude") or None) , float(coordi.get("longitude") or None)]
			
				# customer = frappe.get_value("Customer",username.get("username"),['name'],as_dict=1)
				# data = frappe.db.sql(f"""select a.latitude , a.longitude from `tabAddress` a join `tabDynamic Link` dl on a.name = dl.parent where dl.link_name = '{customer.get("name")}'""",as_dict=True)
				# if data:
				# 	i['coordi'] = [float(data[0].get("latitude") or None),float(data[0].get("longitude") or None)]
				
			i['images_of_orders'] = images_of_orders
			
		
		request[0]['order'] = order
	
		frappe.local.response['http_status_code'] = 200
		return request[0] if request else {"message": "No valid request found."}
	else:
		frappe.local.response['http_status_code'] = 300
		frappe.local.response['message'] = _("No request for this delivery.")	


@frappe.whitelist(allow_guest=True)
def rate_suggest_store(*args,**kwargs):
	try:
		request = kwargs.get("reqId")
		if not request :
			frappe.local.response['http_status_code'] = 500
			frappe.local.response['message'] = _("""Please set the request ID""")
			return
		
		eval = float(kwargs.get("storeEval") or 0) / 5
		if eval:
			doc = frappe.get_doc("Request Delivery",request)
			doc.valuation = eval
			doc.suggest = kwargs.get("storeSugg")
			doc.comment = kwargs.get("storeComment")
			doc.save(ignore_permissions=True)
			frappe.db.commit()
			frappe.local.response['http_status_code'] = 200
			frappe.local.response['message'] = _("""The Store Rated""")

	except Exception as e:
		frappe.log_error(message=str(e), title=_("Error in rate_suggest_store"))
		frappe.local.response['http_status_code'] = 500
		frappe.local.response['message'] = _(e)
		



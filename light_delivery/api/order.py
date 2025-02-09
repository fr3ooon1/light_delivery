import frappe
from frappe import _
from frappe.utils import nowdate , get_first_day_of_week , get_first_day ,  get_datetime, now_datetime, time_diff_in_seconds
from datetime import datetime
from light_delivery.api.apis import get_url , download_image , send_notification , Deductions



@frappe.whitelist(allow_guest=False)
def add_order_to_request(*args, **kwargs):
	try:
		order = kwargs.get("order")
		request = kwargs.get("request")
		if not frappe.db.exists("Request Delivery", request):
			frappe.local.response['http_status_code'] = 400
			frappe.local.response['message'] = "No request like this"
			return

		if not frappe.db.exists("Order", order):
			frappe.local.response['http_status_code'] = 400
			frappe.local.response['message'] = "No order like this"
			return

		doc = frappe.get_doc("Request Delivery", request)

		if doc.status not in ['Pending', 'Waiting for delivery']:
			frappe.local.response['http_status_code'] = 400
			frappe.local.response['message'] = "Cannot add order to this request due to status restrictions."
			return
		
		if doc.number_of_order >= 4:
			frappe.local.response['http_status_code'] = 400
			frappe.local.response['message'] = "Cannot add order to request; maximum order limit reached."
			return
		
		if any(row.order == order for row in doc.order_request):
			frappe.local.response['http_status_code'] = 400
			frappe.local.response['message'] = "Order is already added to this request."
			return

		frappe.db.set_value("Order",order,"request",request)
		doc.append("order_request", {"order": order})
		doc.save(ignore_permissions=True)
		frappe.db.commit()

		frappe.local.response['http_status_code'] = 200
		frappe.local.response['message'] = "The order has been added to the request."
		return
	except Exception as e:
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = f"An error occurred: {e}"

@frappe.whitelist(allow_guest=False)
def update_order(*args , **kwargs):
	try:
		files = frappe.request.files.get('invoice')
		data = frappe.form_dict
		if data.get("order"):
			if frappe.db.exists("Order",data.get("order")):
				order_obj = frappe.get_doc("Order" , data.get("order"))
				
				if order_obj.status in ['Pending','Accepted','Arrived']:
					

					order_obj.full_name = data.get("full_name") if data.get("full_name") else order_obj.full_name
					order_obj.address = data.get("address") if data.get("address") else order_obj.address
					order_obj.zone_address = data.get("zone_address") if data.get("zone_address") else order_obj.zone_address
					order_obj.phone_number = data.get("phone_number") if data.get("phone_number") else order_obj.phone_number
					order_obj.order_type = data.get("order_type") if data.get("order_type") else order_obj.order_type
					order_obj.total_order = data.get("total_order") if data.get("total_order") else order_obj.total_order
					if files:
						image = download_image(files)
						file_url = image.file_url
						order_obj.invoice = file_url
					if order_obj.get("order_type") in ["Refund" , "Replacing"]:
						order_obj.order_reference = data.get("order_reference")
						order_obj.previous_order_amount = data.get("previous_order_amount")
					


					order_obj.save(ignore_permissions=True)
					frappe.db.commit()
					return {"status": "success", "message": "Order updated successfully", "order_name": kwargs.get("order")}
				else:
					frappe.local.response['http_status_code'] = 403
					return {"status": "failed", "message": "can not update order with this status", "order_name": kwargs.get("order")}
		else:
			frappe.local.response['http_status_code'] = 403
			return {"status": "Failed", "message": "No Order Found", "order_name": kwargs.get("order")}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "update_order API error")
		return {"status": "error", "message": str(e)}

@frappe.whitelist(allow_guest=False)
def search_by_phone(phone_number , order_type = False):
	try:
		res = {}
		address = frappe.get_list("Order" , {"phone_number":phone_number},['address'] , pluck='address')
		res['address'] = address
		if order_type in ['Replacing','Refund']:
			orders = frappe.get_list("Order" , {"phone_number":phone_number},['name'] , pluck='name')
			res['order'] = orders 
		return _(res)
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "search_by_phone API error")
		return {"status": "error", "message": str(e)}
	
	
@frappe.whitelist(allow_guest=False)
def search_by_phone_with_total(phone_number , order_type = False):
	try:
		res = {}
		# address = frappe.get_list("Order" , {"phone_number":phone_number},['address'] , pluck='address')
		address = []

		contact = frappe.get_value("Contact",{"mobile_no":phone_number})
		customer = frappe.get_value("Dynamic Link",{"parent":contact},["name","link_name"],as_dict=1)
		if customer:
			customer_name = customer.get("link_name")
			# address_name = frappe.get_value("Dynamic Link",{"link_name":customer_name,"name":["!=" , customer.get("name")]},["name","parent"],as_dict=1)
			# address_st = frappe.get_value("Address",address_name.get("parent"),"address_line1")
			# address.insert(0, address_st)
			address = frappe.db.sql("""SELECT a.address_line1 FROM `tabDynamic Link` dl JOIN `tabAddress` a on a.name = dl.parent WHERE dl.link_name = %s """, (customer_name), pluck='address_line1')

		res['address'] = address
		res['full_name'] = frappe.get_value("Contact",{"mobile_no":phone_number},"first_name")
		if order_type in ['Replacing','Refund']:
			orders = frappe.get_list("Order" , {"phone_number":phone_number,"order_type":"Delivery","order_reference":["!=",None],"reorder":0},['name','total_order'])
			res['order'] = orders 
		return _(res)
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "search_by_phone API error")
		return {"status": "error", "message": str(e)}



@frappe.whitelist(allow_guest=False)
def new_order(*args , **kwargs):
	try:
		user = frappe.session.user
		if not frappe.db.exists("Store" , {"user":user}):
			frappe.local.response['http_status_code'] = 404
			return {
				'status_code': 404,
				'message': 'No store found for this user'
			}
		store = frappe.get_doc("Store" , {"user":user})

		if store.status =="Pending":
			frappe.local.response['http_status_code'] = 404
			frappe.local.response['message'] = _('This Store not activate by Admin.')
			return _('This Store not activate by Admin.')
		

		files = frappe.request.files.get('invoice')
		data = frappe.form_dict


		if ( not data.get("order_type") ) or data.get("order_type") == "" or data.get("order_type") == "Order Type" or data.get("order_type") == None:
			frappe.local.response['http_status_code'] = 404
			frappe.local.response['message'] = _('الرجاء إدخال نوع الطلب')
			return

		if ( not data.get("zone_address") ) or data.get("zone_address") == ""  or data.get("zone_address") == None:
			frappe.local.response['http_status_code'] = 404
			frappe.local.response['message'] = _('الرجاء إدخال عنوان المنطقة')
			return
				

		doc = frappe.new_doc("Order")
		doc.full_name =  data.get('full_name')
		doc.phone_number = data.get('phone_number')
		doc.address= data.get('address')
		doc.order_type= data.get('order_type')
		if data.get("order_type") in ["Refund" , "Replacing"]:
			doc.order_reference = data.get("order_reference")
			doc.previous_order_amount = data.get("previous_order_amount")

		doc.zone_address= data.get('zone_address')
		if files:
			image = download_image(files)
			file_url = image.file_url
			doc.invoice= file_url
		doc.total_order = data.get('total_order')
		doc.store = store.name
		doc.status = "Pending"
		doc.save(ignore_permissions=True)
		frappe.db.commit()
		frappe.local.response['http_status_code'] = 200
		return {"status": "success", "message": "Order created successfully", "order_name": doc.name}

	except Exception as e:
		frappe.local.response['http_status_code'] = 404
		frappe.log_error(frappe.get_traceback(), "new_order API error")
		return {"status": "error", "message": str(e)}

@frappe.whitelist(allow_guest=False)
def get_orders(**kwargs):
	try:
		user = frappe.session.user

		if not frappe.db.exists("Store", {"user": user}):
			frappe.local.response['http_status_code'] = 404
			return {
				'status_code': 404,
				'message': 'No store found for this user'
			}
		store = frappe.get_doc("Store", {"user": user})
		if store:
			pending_request = frappe.get_list(
				"Request Delivery",
				{"store": store.name, "status": ["in", ["Waiting for delivery", "Pending"]], "number_of_order": ["in", [1, 2, 3]]},
				pluck='name',
				ignore_permissions=True
			)
			all_orders = frappe.get_list(
				"Order",
				filters={"store": store.name, "status": "Pending"},
				fields=['name', 'full_name', 'phone_number', 'address', 'zone_address', 'invoice', 'total_order', 'creation', 'status', 'order_type', 'order_reference', 'previous_order_amount', 'differente_amount']
			)
			for order in all_orders:
				order['number_of_images'] = len(frappe.get_doc("Order", order.get("name")).get("order_image"))
				if isinstance(order.get('creation'), datetime):
					order['creation'] = order.get('creation').strftime('%Y-%m-%d %H:%M:%S')
				else:
					order['creation'] = datetime.strptime(order.get('creation'), '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')

			res = {}
			sql = """
					SELECT
						name as id,
						type as en,
						name_in_arabic as ar
					FROM
						`tabOrder Type`
					WHERE enable = 1 ;
			"""
			# order_type = frappe.db.sql(sql,as_dict =1)
			order_type = frappe.get_list("Store Order Type",{"parent":store.name},['order_type as id','type as en','name_in_arabic as ar'],ignore_permissions=True)

			if all_orders:
				res = {
					'status_code': 200,
					'message': _('All Orders'),
					'data': all_orders,
					"pending_request": pending_request,
					"maximum_orders":store.maximum_orders,
					"types":order_type
				}
			else:
				frappe.local.response['http_status_code'] = 200
				res = {
					'status_code': 200,
					'message': _('No Orders Found'),
					'data': all_orders,
					"pending_request": pending_request,
					"maximum_orders":store.maximum_orders,
					"types":order_type
				}
			return res
		else:
			frappe.local.response['http_status_code'] = 403
			return {
				'status_code': 403,
				'message': _('User does not have the required role'),
			}

	except Exception as e:
		frappe.log_error(message=str(e), title=_('Error in get_orders'))
		frappe.local.response['http_status_code'] = 500
		res = {
			"status_code": 500,
			"message": str(e)
		}
		return res
	
@frappe.whitelist(allow_guest=0)
def get_order_type():
	try:
		sql = """
			SELECT
				name as id,
				type as en,
				name_in_arabic as ar
			FROM
				`tabOrder Type`
			WHERE enable = 1 ;
			"""
		order_type = frappe.db.sql(sql,as_dict =1)
		res = {}
		if order_type:
			res = {
				'status_code' : 200 ,
				'message' : _('All data of Order Types') ,
				'data' : order_type
			}
			return res
		else:
			res = {
				'status_code' : 204 ,
				'message' : _('No Order Type Found'),
				'data' : order_type
			}
			return res
		
	except Exception as e:
		frappe.log_error(message=str(e), title=_('Error in get_order_type'))
		frappe.local.response['http_status_code'] = 500
		res = {
			"status_code": 500,
			"message": str(e)
		}
		return res

	
@frappe.whitelist(allow_guest=True)
def get_order(user , order):
	try:
		roles = frappe.get_roles(user)
		if 'Accounts User' in roles:
			order = frappe.get_list("Order" , filters =  {'name':order} , fields = ['*'])
			res = {}
			if order:
				res = {
					'status_code' : 200 ,
					'message' : _('All data of Order') ,
					'data' : order
				}
				return res
			else:
				res = {
					'status_code' : 204 ,
					'message' : _('No Order Found'),
					'data' : order
				}
				return res
		else:
			return {
				'status_code': 403,
				'message': _('User does not have the required role'),
			}
	except Exception as e:
		frappe.log_error(message=str(e), title=_('Error in get_order'))
		frappe.local.response['http_status_code'] = 500
		res = {
			"status_code": 500,
			"message": str(e)
		}
		return res
	

import frappe
from frappe import _

@frappe.whitelist(allow_guest=True)
def get_zone_address():

	try:
		sql = """
			SELECT
				name as id,
				zone as en,
				name_in_arabic as ar
			FROM
				`tabZone Address`
			"""
		zone_addresses = frappe.db.sql(sql,as_dict =1)
		if zone_addresses:
			return {
				'status_code': 200,
				'message': _('All data of Zone Address'),
				'data': zone_addresses
			}
		else:
			return {
				'status_code': 204,
				'message': _('No Zone Address found'),
				'data': []
			}

	except Exception as e:
		frappe.log_error(message=str(e), title=_('Error in get_zone_address'))
		return {
			"status_code": 500,
			"message": str(e)
		}
	


@frappe.whitelist(allow_guest=False)
def get_order_history(status = None):
	try:
		store = frappe.get_value("Store",{"user":frappe.session.user},'name')
		orders = []

		if not status:
			orders = frappe.get_list("Order" , {"store":store} ,['name', 'creation', 'status', 'total_order','valuation','duration','total_distance'])
		elif status and status not in ["All" ,"all" , "ALL" , None]:
			status = status.strip("[]").split(",")
			orders = frappe.get_list("Order" , {'status':['in', status],"store":store} , ['name', 'creation', 'status' , 'total_order','valuation','duration','total_distance'])
		
		
		for order in orders:
			order['total_distance'] = f"""{float(order['total_distance'] or 0) / 1000} KM"""

			if isinstance(order.get('creation'), datetime):
				order['creation'] = order.get('creation').strftime('%Y-%m-%d %H:%M:%S')
			else:
				order['creation'] = datetime.strptime(order.get('creation'), '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
			
			order['valuation'] = float(order['valuation'] or 0) * 5
			
		today = nowdate()
		count_today = frappe.db.count('Order', {'creation': ['>=', today] , 'store':store})

		start_of_week = get_first_day_of_week(today)
		count_this_week = frappe.db.count('Order', {'creation': ['>=', start_of_week] , 'store':store})

		start_of_month = get_first_day(today)
		count_this_month = frappe.db.count('Order', {'creation': ['>=', start_of_month] , 'store':store})

		frappe.local.response['http_status_code'] = 200
		return {
			'status_code': 200,
			'message': _('Order History'),
			'data': {
				'orders': orders,
				'count_today':count_today ,
				'count_this_week' :count_this_week,
				'count_this_month': count_this_month
			}
		}
	except Exception as e:
		frappe.local.response['http_status_code'] = 500
		frappe.log_error(message=str(e), title=_('Error in get_order_history'))
		return str(e)



@frappe.whitelist(allow_guest=False)
def get_order_state():
	try:
		user = frappe.session.user
		store = frappe.get_doc("Store" , {'user':user})
		if store:
			sql = frappe.db.sql(f"""select store_name ,minimum_price , rate_of_km from `tabStore` where user = '{user}' """, as_dict = 1)
			store_priceLise = sql[0] if sql else 0
			
			pending = frappe.db.get_list('Order', {'status': 'Pending','store':store.name})
			accepted = frappe.db.get_list('Order', {'status': 'Accepted','store':store.name})
			on_the_way = frappe.db.get_list('Order', {'status': 'On The Way','store':store.name})
			arrived_for_destination = frappe.db.get_list('Order', {'status': 'Arrived For Destination','store':store.name})
			delivered = frappe.db.get_list('Order', {'status': 'Delivered','store':store.name})
			retunred = frappe.db.get_list('Order', {'status': 'Retunred','store':store.name})
			delivery_cancel = frappe.db.get_list('Order', {'status': 'Delivery Cancel','store':store.name})
			store_cancel = frappe.db.get_list('Order', {'status': 'Store Cancel','store':store.name})
			all_orders = len(pending)+ len(accepted ) + len(on_the_way ) + len(arrived_for_destination ) + len(delivered ) + len(retunred ) + len(delivery_cancel) + len( store_cancel)

			order_states = {
					'pending':len(pending),
					'accepted': len(accepted),
					'on_the_way': len(on_the_way),
					'arrived_for_destination': len(arrived_for_destination),
					'delivered': len(delivered),
					'retunred': len(retunred) , 
					'delivery_cancel': len(delivery_cancel),
					'store_cancel': len(store_cancel),
					'all_orders':all_orders,
				}
			
			"""
			Pending
			Avaliable
			Inorder
			Offline
			"""
			pending = frappe.db.count('Delivery', {'status': 'Pending'})
			avaliable = frappe.db.count('Delivery', {'status': 'Avaliable'})
			Inorder = frappe.db.count('Delivery', {'status': 'Inorder'})
			Offline = frappe.db.count('Delivery', {'status': 'Offline'})
			all_delivery = frappe.db.count('Delivery')

			delivery_states = {
					# 'pending':pending,
					'avaliable':avaliable,
					'Inorder':Inorder,
					# 'Offline':Offline,
					'all_delivery':float(avaliable) + float(Inorder) , 
				}
			
			
			"""
			Pending
			Active
			Inactive
			"""

			store_pending = frappe.db.count('Store', {'status': 'Pending'})
			store_active = frappe.db.count('Store', {'status': 'Active'})
			store_inactive = frappe.db.count('Store', {'status': 'Inactive'})
			all_stores = frappe.db.count('Store')

			stores_states = {
				'store_pending': store_pending,
				'store_active': store_active,
				'store_inactive': store_inactive,
				# 'all_stores': all_stores
			}

			
			frappe.local.response['http_status_code'] = 200
			return {
				'status_code': 200,
				'message': _('Count of order status'),
				'data': {
					'order_states': order_states,
					'delivery_states': delivery_states,
					'store_price_list':store_priceLise,
					# 'stores_states':stores_states
				}
			}

				
		else:
			frappe.local.response['http_status_code'] = 403
			return {
				'status_code': 403,
				'message': _('User does not have the required role'),
				'data': []
			}
	except Exception as e:
		frappe.log_error(message=str(e), title=_('Error in get_order_state'))
		return {
			"status_code": 500,
			"message": str(e)
		}
	


@frappe.whitelist()
def post_zones():
	zones = {
	"MasrElgedidaZones": [
		{ "en": "Korba", "ar": "الكوربة" },
		{ "en": "Roxy", "ar": "روكسي" },
		{ "en": "Heliopolis", "ar": "هيليوبوليس" },
		{ "en": "Almazah", "ar": "الماظة" },
		{ "en": "Alf Maskan", "ar": "ألف مسكن" },
		{ "en": "Midan El-Gama'a", "ar": "ميدان الجامعة" },
		{ "en": "Saint Fatima", "ar": "سانت فاتيما" },
		{ "en": "Ard El-Golf", "ar": "أرض الجولف" },
		{ "en": "Al-Mirghani", "ar": "المرغني" },
		{ "en": "Salah El-Din Square", "ar": "ميدان صلاح الدين" }
	],
	"NasrCityZones": [
		{ "en": "1st District", "ar": "الحي الأول" },
		{ "en": "2nd District", "ar": "الحي الثاني" },
		{ "en": "3rd District", "ar": "الحي الثالث" },
		{ "en": "4th District", "ar": "الحي الرابع" },
		{ "en": "5th District", "ar": "الحي الخامس" },
		{ "en": "6th District", "ar": "الحي السادس" },
		{ "en": "7th District", "ar": "الحي السابع" },
		{ "en": "8th District", "ar": "الحي الثامن" },
		{ "en": "9th District", "ar": "الحي التاسع" },
		{ "en": "10th District", "ar": "الحي العاشر" },
		{ "en": "Madinet Nasr", "ar": "مدينة نصر" },
		{ "en": "Makram Ebeid", "ar": "مكرم عبيد" },
		{ "en": "Tayaran Street", "ar": "شارع الطيران" },
		{ "en": "Abbas El-Akkad Street", "ar": "شارع عباس العقاد" }
	]
	}

	masrElgedidaZones = zones.get("MasrElgedidaZones")
	for i in masrElgedidaZones:
		doc = frappe.new_doc("Zone Address")
		doc.zone = i.get("en")
		doc.name_in_arabic = i.get("ar")
		doc.save(ignore_permissions = True)
		frappe.db.commit()


@frappe.whitelist(allow_guest=False)
def cancel_order(*args,**kwargs):
	order = kwargs.get("order")
	notification_key = None
	if frappe.db.exists("Order" , order):
		order_obj = frappe.get_doc("Order" , order )
		if kwargs.get("type") == 'store':
			order_obj.status = "Cancel"
			order_obj.cancel_from = "Store"
			msg = f"""Order had been cancel by Store"""
			delivery = frappe.get_value("Delivery",order_obj.delivery,"user")
			notification_key = frappe.get_value("User",delivery,'notification_key')

		if kwargs.get("type") == 'delivery':
			order_obj.status = "Cancel"
			order_obj.cancel_from = "Delivery"
			msg = f"""Order had been cancel by Store"""

			user = frappe.get_value("Store",order_obj.store,"user")
			notification_key = frappe.get_value("User",user,'notification_key')

		
		res = send_notification(notification_key, "modification")
		if res.status_code != 200:
			error = frappe.new_doc("Error Log")
			error.method = "send_notification"
			error.error = res.text
			error.insert(ignore_permissions=True)

		order_obj.save(ignore_permissions=True)
		frappe.db.commit()
		frappe.local.response['http_status_code'] = 200
		frappe.local.response['message'] = _(msg)
	else:
		frappe.local.response['http_status_code'] = 300
		frappe.local.response['message'] = _(f"""no order like {order}""")



@frappe.whitelist(allow_guest=False)
def change_order_status_del(*args, **kwargs):
	order = kwargs.get("order")
	status = kwargs.get("status")
	notification_key = None
	Deductions = frappe.get_doc("Deductions")

	if not order or not status:
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = _("Order and status are required.")
		return

	if not frappe.db.exists("Order", order):
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = _(f"No order found with ID: {order}")
		return

	try:
		doc = frappe.get_doc("Order", order)

		# Determine notification key
		if frappe.db.exists("Delivery", {"user": frappe.session.user}):
			if doc.store:
				user = frappe.get_value("Store", doc.store, "user")
				notification_key = frappe.get_value("User", user, "notification_key")
		else:
			if doc.delivery:
				user = frappe.get_value("Delivery", doc.delivery, "user")
				notification_key = frappe.get_value("User", user, "notification_key")

		# Handle refused status with time constraints
		if status == "Refused":
			order_logs = frappe.db.sql(
				"""SELECT status, time FROM `tabOrder Log` WHERE parent = %s""",
				(order,),
				as_dict=True,
			)
			
			arrived_row = next((row for row in order_logs if row['status'] == "Arrived For Destination"), None)

			if arrived_row:
				time_difference = time_diff_in_seconds(now_datetime(), get_datetime(arrived_row.get("time")))
				if float(time_difference / 60) < (float(Deductions.time_of_waiting_customer_to_answer or 0)):
					frappe.local.response['http_status_code'] = 400
					frappe.local.response['message'] = _(f"Cannot change status to {status} due to time restrictions.")
					return

		# Update order status and save
		doc.status = status
		doc.save(ignore_permissions=True)
		frappe.db.commit()

		# Send notification
		if notification_key:
			res = send_notification(notification_key, "modification")
			if res.status_code != 200:
				frappe.log_error(
					message=res.text, 
					title=_("Error sending notification")
				)
				error = frappe.new_doc("Error Log")
				error.method = "send_notification"
				error.error = res.text
				error.insert(ignore_permissions=True)

		# Response on success
		frappe.local.response['http_status_code'] = 200
		frappe.local.response['message'] = _(f"The order {order} has been updated successfully.")

	except Exception as e:
		# Log unexpected errors and respond with error message
		frappe.log_error(message=str(e), title=_(f"""Error in change_order_status_del in order {order}"""))
		frappe.local.response['http_status_code'] = 500
		frappe.local.response['message'] = _("An error occurred while updating the order.")


@frappe.whitelist(allow_guest=True)
def rate_order_del(*args,**kwargs):
	try:
		order = kwargs.get("orderId")
		if not order :
			frappe.local.response['http_status_code'] = 500
			frappe.local.response['message'] = _("""Please set the order ID""")
			return
		
		eval = float(kwargs.get("deliveryEval") or 0) / 5
		if eval:
			doc = frappe.get_doc("Order",order)
			doc.valuation = eval
			doc.suggest = kwargs.get("deliverySugg")
			doc.comment = kwargs.get("deliveryComment")
			doc.save(ignore_permissions=True)
			frappe.db.commit()
			frappe.local.response['http_status_code'] = 200
			frappe.local.response['message'] = _("""The Delivery Rated""")

	except Exception as e:
		frappe.log_error(message=str(e), title=_("Error in rate_order_del"))
		frappe.local.response['http_status_code'] = 500
		frappe.local.response['message'] = _(e)
import frappe
from frappe import _
from frappe.utils import nowdate , get_first_day_of_week , get_first_day , getdate , get_site_base_path
from datetime import datetime
from light_delivery.api.apis import get_url
from light_delivery.api.apis import download_image


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
		return res
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

		files = frappe.request.files.get('invoice')
		data = frappe.form_dict

		

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
		doc.save(ignore_permissions=True)
		frappe.db.commit()
		frappe.local.response['http_status_code'] = 200
		return {"status": "success", "message": "Order created successfully", "order_name": doc.name}

	except Exception as e:
		frappe.local.response['http_status_code'] = 404
		frappe.log_error(frappe.get_traceback(), "new_order API error")
		return {"status": "error", "message": str(e)}

@frappe.whitelist(allow_guest=False)
def get_orders():
	try:
		user = frappe.session.user

		if not frappe.db.exists("Store" , {"user":user}):
			frappe.local.response['http_status_code'] = 404
			return {
				'status_code': 404,
				'message': 'No store found for this user'
			}
		store = frappe.get_doc("Store" , {"user":user})
		if store:

			all_orders = frappe.get_list(
				"Order",
				filters={"store": store.name, "status": "Pending"},
				fields=['name', 'full_name', 'phone_number', 'address','zone_address', 'invoice', 'total_order', 'creation' ,'status','order_type','order_reference' ,'previous_order_amount','differente_amount']
			)
			for order in all_orders:

				order['number_of_images'] = len(frappe.get_doc("Order",order.get("name")).get("order_image"))
				if isinstance(order.get('creation'), datetime):
					order['creation'] = order.get('creation').strftime('%Y-%m-%d %H:%M:%S')
				else:
					order['creation'] = datetime.strptime(order.get('creation'), '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
				invoice = order.get("invoice")
				if invoice:
					file = frappe.get_doc("File", {"file_url": invoice})
					url = get_url()
					order['invoice'] = url + file.file_url
					

			res = {}
			if all_orders:
				res = {
					'status_code': 200,
					'message': _('All Orders'),
					'data': all_orders
				}
			else:
				frappe.local.response['http_status_code'] = 200
				res = {
					'status_code': 200,
					'message': _('No Orders Found'),
					'data': all_orders
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
	


@frappe.whitelist(allow_guest=True)
def get_order_history(status = None):
	# status = status.split(",")

	# return status
	try:
		orders = []

		if status == None or status == "All" or status == "ALL" or status == "all":
			orders = frappe.get_list("Order" ,  fields=['name', 'creation', 'status', 'total_order'])
		else:
			status = status.strip("[]").split(",")
			orders = frappe.get_list("Order" , filters = {'status':['in', status]} ,  fields=['name', 'creation', 'status' , 'total_order'])
		
		
		for order in orders:
			if isinstance(order.get('creation'), datetime):
				order['creation'] = order.get('creation').strftime('%Y-%m-%d %H:%M:%S')
			else:
				order['creation'] = datetime.strptime(order.get('creation'), '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
			
		today = nowdate()
		count_today = frappe.db.count('Order', filters={'creation': ['>=', today]})

		start_of_week = get_first_day_of_week(today)
		count_this_week = frappe.db.count('Order', filters={'creation': ['>=', start_of_week]})

		start_of_month = get_first_day(today)
		count_this_month = frappe.db.count('Order', filters={'creation': ['>=', start_of_month]})

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
		frappe.log_error(message=str(e), title=_('Error in get_order_history'))
		return {
			"status_code": 500,
			"message": str(e)
		}



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


 
# def download_image(url):
# 	try:
# 		site_path = os.path.abspath(os.getcwd()) + get_site_base_path()[1::]+"/public/files"
# 		access_token = frappe.db.get_single_value('DMS Settings', 'response')
# 		headers = {
# 			"Authorization": f"Bearer {access_token}",
# 			"Content-Type": "application/json"
# 		}

# 		response = requests.get(url,headers=headers, stream=True)
# 		response.raise_for_status()  # Raise an exception for error HTTP status codes
# 		# Ensure the directory exists
# 		image_name = url.split('/')
# 		with open(os.path.join(site_path, f'{image_name[-1]}'), 'wb') as f:
# 			for chunk in response.iter_content(1024):
# 				f.write(chunk)
# 		#create File To frappe 
# 		with open(os.path.join(site_path, f'{image_name[-1]}'), 'rb') as image_file:
# 			encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
# 		new_file = frappe.new_doc("File")
# 		new_file.file_name = f'{image_name[-1]}'
# 		new_file.is_private = 0 
# 		new_file.filedata = encoded_string
# 		new_file.file_url ="/files/"+ f'{image_name[-1]}'
# 		new_file.save(ignore_permissions = True)
# 		frappe.db.commit()
# 		return new_file.name
# 	except requests.exceptions.RequestException as e:
# 		print(f"Error downloading image: {e}")
# 		return False



@frappe.whitelist(allow_guest=False)
def cancel_order(*args,**kwargs):
	order = kwargs.get("order")
	if frappe.db.exists("Order" , order):
		order_obj = frappe.get_doc("Order" , order )
		if kwargs.get("type") == 'store':
			order_obj.status = "Store Cancel"
			msg = f"""Order had been cancel by Store"""

		if kwargs.get("type") == 'delivery':
			order_obj.status = "Delivery Cancel"
			msg = f"""Order had been cancel by Store"""

		order_obj.save(ignore_permissions=True)
		frappe.db.commit()
		frappe.local.response['http_status_code'] = 200
		frappe.local.response['message'] = _(msg)
	else:
		frappe.local.response['http_status_code'] = 300
		frappe.local.response['message'] = _(f"""no order like {order}""")




@frappe.whitelist(allow_guest=False)
def change_order_status_del(*args,**kwargs):
	user = frappe.session.user
	delivery = frappe.get_value("Delivery",{"user":user},'name')

	order = kwargs.get("order")
	status = kwargs.get("status")

	if frappe.db.exists("Order" , order):
		doc = frappe.get_doc("Order" , order)
		if doc.delivery == delivery :
			doc.status = status
			doc.save(ignore_permissions=True)
			frappe.db.commit()
			frappe.local.response['http_status_code'] = 200
			frappe.local.response['message'] = _(f"""The {order} had been changes.""")
		else:
			frappe.local.response['http_status_code'] = 300
			frappe.local.response['message'] = _(f"""This {delivery} not the driver.""")
	else:
		frappe.local.response['http_status_code'] = 300
		frappe.local.response['message'] = _(f"""no order like {order}""")
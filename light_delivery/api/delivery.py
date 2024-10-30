import frappe
from frappe import _
from light_delivery.api.delivery_request import calculate_balane
from light_delivery.api.apis import download_image


@frappe.whitelist()
def get_all_customers(user = None):
	
	try:
		user = frappe.session.user
		all_customers = frappe.get_list("Customer",filters = {"disabled" : 0} ,fields=['customer_name','customer_type','customer_group','territory','default_price_list'])
		res = {}
		if all_customers:
			res = {
				'status_code' : 200 ,
				'message' : 'All Customers' ,
				'data' : all_customers
			}
			return res
		else:
			res = {
				'status_code' : 500 ,
				'message' : 'No Customers Found',
				'data' : all_customers
			}
			return res
	except Exception as e:
		res = {
			"status_code": 404,
			"message": str(e)
		}
		return res
	

@frappe.whitelist(allow_guest=False)
def get_profile():
	try:
		user = frappe.get_value("User",frappe.session.user,['full_name','mobile_no'],as_dict=True)
		
		res = {}
		if frappe.db.exists("Delivery",{"user":frappe.session.user}):
			delivery = frappe.get_value("Delivery",{"user":frappe.session.user},['date_of_joining','license_expire','name','image','national_id','delivery_category'], as_dict=1)
			price_list = frappe.get_value("Delivery Category" , delivery.get("delivery_category"), ['minimum_orders' , 'maximum_orders' , 'maximum_order_by_request' , 'minimum_rate' , 'rate_of_km'],as_dict=1)
			res = {
				"full_name":user.get("full_name"),
				"phone_number":user.get("mobile_no"),
				"date_of_joining":delivery.get("date_of_joining"),
				"license_expire":delivery.get("license_expire"),
				"national_id":delivery.get("national_id"),
				"wallet": float(calculate_balane(delivery.get("name")) or 0),
				"price_list":price_list,
				"image":delivery.get("image")
			}
		# if frappe.db.exists("Store",frappe.session.user):
		# 	store = frappe.get_doc("Store",frappe.session.user)


		return res
		
	except Exception as e:
		frappe.log_error(message=str(e), title=_(e))
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = _(e)
	

@frappe.whitelist(allow_guest=False)
def change_profile_pic():
	try:
		files = frappe.request.files
		image = download_image(files.get('image'))

		if frappe.db.exists("Delivery",{"user":frappe.session.user}):
			delivery = frappe.get_doc("Delivery",{"user":frappe.session.user})
			delivery.image = image.file_url
			delivery.save(ignore_permissions=True)
			frappe.db.commit()
			return f"""image updated successfully"""
		else:
			frappe.local.response['http_status_code'] = 400
			return f"""no delivery like this name {frappe.session.user}"""

		
	except Exception as e:
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = _(e)



@frappe.whitelist(allow_guest=False)
def delivery_tracing(*args,**kwargs):
	res = {
		"start":[],
		"end":[],
		"point_list":[]
	}
	
	try:
		point_list = []
		request = kwargs.get("request")
		if frappe.db.exists("Request Delivery",request):
			doc = frappe.get_doc("Request Delivery",request)
			orders = doc.get("order_request")
			if orders:
				for order in orders:
					order_obj = frappe.get_doc("Order",order.order)
					road = order_obj.get("road")
					for i in road:
						point_list.append({"GeoPoint":{
											"latitude": i.pointer_y,
											"longitude": i.pointer_x,
											}})
			res = {
				"start":point_list[0],
				"end":point_list[-1],
				"point_list":point_list
			}
			return res
		else:
			frappe.local.response['http_status_code'] = 400

	except Exception as e:
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = _(e)
	

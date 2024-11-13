import frappe
from frappe import _
from light_delivery.api.delivery_request import get_balance
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
		user = frappe.get_value("User",frappe.session.user,['full_name','mobile_no','email','username','first_name'],as_dict=True)
		
		res = {}
		if frappe.db.exists("Delivery",{"user":frappe.session.user}):
			delivery = frappe.get_value("Delivery",{"user":frappe.session.user},['date_of_joining','license_expire','name','image','national_id','delivery_category','delivery_name'], as_dict=1)
			price_list = frappe.get_value("Delivery Category" , delivery.get("delivery_category"), ['minimum_orders' , 'maximum_orders' , 'maximum_order_by_request' , 'minimum_rate' , 'rate_of_km'],as_dict=1)

			res['date_of_joining'] = delivery.get("date_of_joining")
			res['license_expire'] = delivery.get("license_expire")
			res['national_id'] = delivery.get("national_id")
			res['wallet'] = float(get_balance(user.get("first_name")) or 0)
			res['price_list'] = price_list
			# res['image'] = delivery.get("image")
			
		elif frappe.db.exists("Store",{"user":frappe.session.user}):
			pass
		
		address = frappe.db.sql(f"""select a.address_line1 from `tabAddress` a join `tabDynamic Link` dl on a.name = dl.parent where dl.link_name = '{user.get("username")}'""")

		res["full_name"]=user.get("full_name")
		res["phone_number"]=user.get("mobile_no")
		res["email"]=user.get("email")
		res["address"]=address[0].get("address_line1") if address else None
		res["image"]=frappe.get_value("Customer",user.get("username"),'image')
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

		username = frappe.get_value("User",frappe.session.user,'username')

		if frappe.db.exists("Customer",username):
			doc = frappe.get_doc("Customer",username)
			doc.image = image.file_url
			doc.save(ignore_permissions=True)
			frappe.db.commit()
			return f"""image updated successfully"""
		else:
			frappe.local.response['http_status_code'] = 400
			return f"""no user like {frappe.session.user}"""
		
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
			delivery = frappe.get_value("Request Delivery",request,"delivery")
			start = {
				"GeoPoint":{
						"latitude": float(frappe.get_value("Request Delivery",request,"lon")),
						"longitude": float(frappe.get_value("Request Delivery",request,"lat")),
				}}
			end = {
				"GeoPoint":{
						"latitude": float(frappe.get_value("Delivery",delivery,"pointer_y")),
						"longitude": float(frappe.get_value("Delivery",delivery,"pointer_x")),
				}}
			# orders = doc.get("order_request")
			# orders = frappe.get_list("Order Request",{"parent":request},pluck='order',ignore_permissions=True)
			# if orders:
			# 	for order in orders:
			# 		order_obj = frappe.get_doc("Order",order.order)
			# 		road = order_obj.get("road")
			# 		if road:
			# 			for i in road:
			# 				point_list.append({"GeoPoint":{
			# 									"latitude": i.pointer_y,
			# 									"longitude": i.pointer_x,
			# 							}})
			# if not point_list:
			# 	frappe.local.response['http_status_code'] = 400
			# 	frappe.local.response['message'] = _(f"""no point found""")
			# 	return
			res = {
				"start":start,
				"end":end,
				"point_list":[start,end]
			}
			return res
		else:
			frappe.local.response['http_status_code'] = 400
			frappe.local.response['message'] = _(f"""no request found""")
	# try:

	# 	request = kwargs.get("request")
	# 	if frappe.db.exists("Request Delivery",request):
	# 		delivery = frappe.get_value("Request Delivery" , request , "delivery")
	# 		doc = frappe.get_doc("Delivery",delivery)
	# 		coordi = {
	# 			"latitude":doc.pointer_y,
	# 			"longitude":doc.pointer_x
	# 		}
	# 		last_modification = str(doc.modified)

	# 		frappe.local.response['http_status_code'] = 200
	# 		frappe.local.response['GeoPoint'] = coordi
	# 		frappe.local.response['last_modification'] = last_modification

	except Exception as e:
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = _(e)
	

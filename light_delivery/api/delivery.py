import frappe
from frappe import _
from light_delivery.api.delivery_request import get_balance
from light_delivery.api.apis import download_image


@frappe.whitelist(allow_guest=False)
def post_suggestion(**kwargs):
	try:
		user = frappe.session.user
		
		if frappe.db.exists("Delivery",{"user":user}):
			doc = frappe.new_doc("Complaints")
			doc.from_type = "Delivery"
			from_user = frappe.get_value("Delivery",{"user":user},"name")
			doc.from_user = from_user
			doc.complaints = kwargs.get("complaints") if kwargs.get("complaints") else None
			doc.suggestion = kwargs.get("suggestion") if kwargs.get("suggestion") else None
			doc.save(ignore_permissions=True)
			frappe.db.commit()
		elif frappe.db.exists("Store",user):
			doc = frappe.new_doc("Complaints")
			doc.from_type = "Store"
			from_user = frappe.get_value("Store",{"user":user},"name")
			doc.from_user = from_user
			doc.complaints = kwargs.get("complaints") if kwargs.get("complaints") else None
			doc.suggestion = kwargs.get("suggestion") if kwargs.get("suggestion") else None
			doc.save(ignore_permissions=True)
			frappe.db.commit()

			
		frappe.local.response['http_status_code'] = 200
		frappe.local.response['message'] = _("Suggestion sent successfully")
			
	except Exception as e:
		frappe.log_error(message=str(e), title="Error in post_suggestion")
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = _(e)	



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
		customer = frappe.db.sql("""  
						select 
							cc.link_name as link_name
						from 
						   `tabContact` as c  
						join 
						   `tabDynamic Link` as cc 
						on 
							cc.parent = c.name 
						where 
						   c.user = %s ; """, values=(user.get("email"),), as_dict=True)
		if customer:
			customer = customer[0].get("link_name")

		address = frappe.db.sql(f"""select a.name as id , a.address_line1 , a.latitude , a.longitude from `tabAddress` a join `tabDynamic Link` dl on a.name = dl.parent where dl.link_name = '{user.get("username")}'""",as_dict=True)
		
		res = {}
		if frappe.db.exists("Delivery",{"user":frappe.session.user}):
			delivery = frappe.get_value("Delivery",{"user":frappe.session.user},['date_of_joining','license_expire','name','image','national_id','delivery_category','delivery_name'], as_dict=1)
			price_list = frappe.get_value("Delivery Category" , delivery.get("delivery_category"), ['minimum_orders' , 'maximum_orders' , 'maximum_order_by_request' , 'minimum_rate' , 'rate_of_km'],as_dict=1)

			res['date_of_joining'] = delivery.get("date_of_joining")
			res['license_expire'] = delivery.get("license_expire")
			res['national_id'] = delivery.get("national_id")
			res['wallet'] = float(get_balance(customer) or 0) if customer else 0.0
			res['price_list'] = price_list
			# res['image'] = delivery.get("image")
			res['image'] = frappe.get_value("Delivery",{"user":frappe.session.user},'image')
			res["address"]=address[0].get("address_line1") if address else None
			
		elif frappe.db.exists("Store",{"user":frappe.session.user}):
			pass
		else:
			res['image'] = frappe.get_value("Customer",user.get("username"),'image')
			res["address"]= address if address else None

		
		

		res["full_name"]=user.get("full_name")
		res["phone_number"]=user.get("mobile_no")
		res["email"]=user.get("email")
		
		# res["image"]=frappe.get_value("Customer",user.get("username"),'image')
		return res
		
	except Exception as e:
		frappe.log_error(message=str(e), title=_(e))
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = _(e)
	

@frappe.whitelist(allow_guest=False)
def change_profile_pic():
	try:
		files = frappe.request.files

		if files.get('image'):
			image = download_image(files.get('image'))

		if files.get('store_cover'):
			store_cover = download_image(files.get('store_cover'))
		
		if files.get('store_logo'):
			store_logo = download_image(files.get('store_logo'))

		username = frappe.session.user

		if frappe.db.exists("Delivery",{"user":username}):	
			doc = frappe.get_doc("Delivery",{"user":username})
			doc.image = image.file_url
			doc.save(ignore_permissions=True)
			frappe.db.commit()
			return f"""image updated successfully"""

		elif frappe.db.exists("Customer",username):
			doc = frappe.get_doc("Customer",username)
			doc.image = image.file_url
			doc.save(ignore_permissions=True)
			frappe.db.commit()
			return f"""image updated successfully"""
		elif frappe.db.exists("Store",username):
			doc = frappe.get_doc("Store",username)

			if store_cover:
				doc.store_cover = store_cover.file_url
			if store_logo:
				doc.store_logo = store_logo.file_url
				
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
			res = {
				"start":start,
				"end":end,
				"point_list":[start,end]
			}
			return res
		else:
			frappe.local.response['http_status_code'] = 400
			frappe.local.response['message'] = _(f"""no request found""")

	except Exception as e:
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = _(e)
	

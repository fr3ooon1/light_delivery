import frappe 
from frappe import _
from frappe.utils import add_to_date, today, nowdate
from frappe.utils import nowdate , get_first_day_of_week , get_first_day ,  get_datetime, now_datetime, time_diff_in_seconds
from datetime import datetime
from light_delivery.api.apis import search_by_zone , download_image , haversine




@frappe.whitelist()
def validate(self , method):
	getcontact(self)

def getcontact(self):
	if not self.mobile_no:
		if frappe.db.exists("Dynamic Link", {"parenttype": "Contact", "link_doctype": "Customer", "link_name": self.name}):
			dynamic_link = frappe.get_value(
				"Dynamic Link", 
				{
					"parenttype":"Contact", 
					"link_doctype":"Customer", 
					"link_name":self.name
				},
				["parent"])
			if dynamic_link:
				self.customer_primary_contact = dynamic_link
				self.mobile_no = frappe.get_value("Contact", dynamic_link, "mobile_no")
				self.email_id = frappe.get_value("Contact", dynamic_link, "email_id")

		
		

@frappe.whitelist(allow_guest=True)
def get_slider():
	today = nowdate() 
	res = []
	try:
	
		valid_stores = frappe.get_all(
			"Offers", 
			filters={
				"valid_from": ["<=", today],
				"valid_to": [">=", today]
			},
			fields=["from as store" , "offer as ads"] 
		)
		user = frappe.get_value("User", frappe.session.user ,["username","full_name"],as_dict=True)
		customer = frappe.get_value("Customer",user.get("username"),'name')
		address = frappe.db.sql(f"""select a.address_line1 , a.latitude , a.longitude from `tabAddress` a join `tabDynamic Link` dl on a.name = dl.parent where a.is_current_location = 1 and dl.link_name = '{customer}'""",as_dict=True)
		if not address:
			address = frappe.db.sql(f"""select a.address_line1 , a.latitude , a.longitude from `tabAddress` a join `tabDynamic Link` dl on a.name = dl.parent where dl.link_name = '{customer}'""",as_dict=True)
		
		if not address:
			frappe.local.response['http_status_code'] = 400
			frappe.local.response['message'] = "Latitude and Longitude are required."
			return
		
		address = address[-1] if address else None
		coordi = [float(address.get("latitude")),float(address.get("longitude"))] if address else [None,None]
		
		for store in valid_stores:
			doc = frappe.get_doc("Store",store.get("store"))
			duration = 0

			if  (doc.pointer_y and  doc.pointer_x) and (coordi[0] and coordi[1]):
				duration = haversine(
					[float(doc.pointer_y or 0), float(doc.pointer_x or 0)], 
					coordi
				)

			res.append({
				"ads":store.get("ads"),
				"id":doc.name,
				"is_favorite":is_favorite(user.get("username") , store.get("store")),
				"cover":doc.store_cover,
				"logo":doc.store_logo,
				"store_name":frappe.get_value("User",doc.user,"full_name"),
				"location":[doc.pointer_y,doc.pointer_x] if doc.pointer_y and doc.pointer_x else [],
				"address":doc.address,
				"phone": frappe.get_value("User",doc.user,"mobile_no"),
				"delivery_time":10,
				"menu":frappe.get_list("Menu",{"parent":doc.name},pluck='menu',ignore_permissions=True),
				"duration":duration
			})
		
		res = sorted(res, key=lambda x: x['duration'], reverse=False)
		
		frappe.local.response['http_status_code'] = 200
		frappe.local.response['message'] = res

	except Exception as e:
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = f"An error occurred: {e}"


@frappe.whitelist(allow_guest=True)
def get_stores(*args,**kwargs):
	try:
		idx=0
		if kwargs.get("category"):
			category = kwargs.get("category")
			tot_stores = frappe.db.count('Store',{"store_category":category})
		else:
			tot_stores = frappe.db.count('Store')
		pages = (tot_stores/10)
		if pages%10 > 0:
			pages = int(pages) +1

		if kwargs.get("idx"):
			idx = float(kwargs.get("idx") or 0) -1

		start = idx * 10
		page_length=10
		order_by = "idx"

		if kwargs.get("category"):
			category = kwargs.get("category")
			stores = frappe.db.get_list("Distance",{"store_category":category},['store as id' , 'distance'],order_by=order_by,start=start,page_length=page_length,ignore_permissions=True)
		else:
			stores = frappe.db.get_list("Distance",['store as id' , 'distance'],order_by=order_by,start=start,page_length=page_length,ignore_permissions=True)

		res = []

		user = frappe.get_value("User",frappe.session.user,["username","full_name"],as_dict=True)
		customer = frappe.get_value("Customer",user.get("username"),'name')

		address = frappe.db.sql(f"""select a.address_line1 , a.latitude , a.longitude from `tabAddress` a join `tabDynamic Link` dl on a.name = dl.parent where a.is_current_location = 1 and dl.link_name = '{customer}'""",as_dict=True)
		if not address:
			address = frappe.db.sql(f"""select a.address_line1 , a.latitude , a.longitude from `tabAddress` a join `tabDynamic Link` dl on a.name = dl.parent where dl.link_name = '{customer}'""",as_dict=True)
		
		
		# address = address[-1] if address else None
		
		# coordi = [float(address.get("latitude")),float(address.get("longitude"))] if address else [None,None]
		
		for store in stores:
			doc = frappe.get_doc("Store",store.get("id"))
			duration = 0

			if  (doc.pointer_y and  doc.pointer_x) :
				duration = float(store.get("distance") or 0)

			res.append({
				"id":doc.name,
				"is_favorite":is_favorite(user.get("username") , store.get("id")),
				"cover":doc.store_cover,
				"logo":doc.store_logo,
				"store_name":frappe.get_value("User",doc.user,"full_name"),
				"location":[doc.pointer_y,doc.pointer_x] if doc.pointer_y and doc.pointer_x else [],
				"address":doc.address,
				"phone": frappe.get_value("User",doc.user,"mobile_no"),
				"delivery_time":10,
				"menu":frappe.get_list("Menu",{"parent":doc.name},pluck='menu',ignore_permissions=True),
				"duration":f"{round(duration , 2)} KM"
			})
		# res = sorted(res, key=lambda x: x['duration'], reverse=False)
		frappe.local.response['http_status_code'] = 200
		frappe.local.response['data'] = res
		frappe.local.response['message'] = pages
	except Exception as e:
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = f"An error occurred: {e}"
		frappe.log_error(message=str(e), title=_('Error in get_stores'))


@frappe.whitelist(allow_guest=True)
def get_home_stories():
	try:
		res = []
		stores = frappe.get_list("Store",{"show_in_home":1,"status":"Active"},['name'],ignore_permissions=True)
		user = frappe.get_value("User",frappe.session.user,["username","full_name","mobile_no"],as_dict=True)

		customer = frappe.get_value("Customer",user.get("username"),'name')

		address = frappe.db.sql(f"""select a.address_line1 , a.latitude , a.longitude from `tabAddress` a join `tabDynamic Link` dl on a.name = dl.parent where a.is_current_location = 1 and dl.link_name = '{customer}'""",as_dict=True)
		if not address:
			address = frappe.db.sql(f"""select a.address_line1 , a.latitude , a.longitude from `tabAddress` a join `tabDynamic Link` dl on a.name = dl.parent where dl.link_name = '{customer}'""",as_dict=True)
		
		
		address = address[-1] if address else None
		
		coordi = [float(address.get("latitude")),float(address.get("longitude"))] if address else [None,None]
		for store in stores:
			doc = frappe.get_doc("Store",store.get("name"))

			duration = 0

			if  (doc.pointer_y and  doc.pointer_x) and (coordi[0] and coordi[1]):
				duration = haversine(
					[float(doc.pointer_y or 0), float(doc.pointer_x or 0)], 
					coordi
				)
			res.append({
				"id":doc.name,
				"is_favorite":is_favorite(user.get("username") , store.get("name")),
				"cover":doc.store_cover,
				"logo":doc.store_logo,
				"store_name":frappe.get_value("User",doc.user,"full_name"),
				"location":[doc.pointer_y,doc.pointer_x] if doc.pointer_y and doc.pointer_x else [],
				"address":doc.address,
				"phone": frappe.get_value("User",doc.user,"mobile_no"),
				"delivery_time":10,
				"menu":frappe.get_list("Menu",{"parent":doc.name},pluck='menu',ignore_permissions=True),
				"duration":f"{round(duration , 2)} KM"
			})
		res = sorted(res, key=lambda x: x['duration'], reverse=False)
		frappe.local.response['http_status_code'] = 200
		frappe.local.response['message'] = res
			
	except Exception as e:
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = f"An error occurred: {e}"
		frappe.log_error(message=str(e), title=_('Error in get_home_stories'))



@frappe.whitelist(allow_guest=False)
def get_favorite(*args,**kwargs):
	res = []
	user = frappe.get_value("User",frappe.session.user,["username","full_name","mobile_no"],as_dict=True)
	if frappe.db.exists("Favorite",user.get("username")):
		stores = frappe.get_list("Stores",{"parent":user.get("username")},['store'],ignore_permissions=True)
		customer = frappe.get_value("Customer",user.get("username"),'name')

		address = frappe.db.sql(f"""select a.address_line1 , a.latitude , a.longitude from `tabAddress` a join `tabDynamic Link` dl on a.name = dl.parent where a.is_current_location = 1 and dl.link_name = '{customer}'""",as_dict=True)
		if not address:
			address = frappe.db.sql(f"""select a.address_line1 , a.latitude , a.longitude from `tabAddress` a join `tabDynamic Link` dl on a.name = dl.parent where dl.link_name = '{customer}'""",as_dict=True)
		
		
		address = address[-1] if address else None
		
		coordi = [float(address.get("latitude")),float(address.get("longitude"))] if address else [None,None]
		for store in stores:
			doc = frappe.get_doc("Store",store.get("store"))

			duration = 0

			if  (doc.pointer_y and  doc.pointer_x) and (coordi[0] and coordi[1]):
				duration = haversine(
					[float(doc.pointer_y or 0), float(doc.pointer_x or 0)], 
					coordi
				)

			res.append({
				"id":doc.name,
				"is_favorite":is_favorite(user.get("username") , store.get("store")),
				"cover":doc.store_cover,
				"logo":doc.store_logo,
				"store_name":frappe.get_value("User",doc.user,"full_name"),
				"location":[doc.pointer_y,doc.pointer_x] if doc.pointer_y and doc.pointer_x else [],
				"address":doc.address,
				"phone": frappe.get_value("User",doc.user,"mobile_no"),
				"delivery_time":10,
				"menu":frappe.get_list("Menu",{"parent":doc.name},pluck='menu',ignore_permissions=True),
				"duration":f"{round(duration , 2)} KM"
			})
		res = sorted(res, key=lambda x: x['duration'], reverse=False)
		return res
	else:
		fav = frappe.new_doc("Favorite")
		fav.customer = user.get("username")
		fav.insert(ignore_permissions=True)
		frappe.db.commit()
		return res
	

@frappe.whitelist(allow_guest=True)
def check_version(**kwargs):
	version = kwargs.get("version")
	customer_versions = frappe.get_list("Customer Version",{"parent":"Deductions"},pluck="version",ignore_permissions=True)
	
	if not version:
		return False
	else:
		if version not in  customer_versions:
			return False
		else:
			return True


@frappe.whitelist(allow_guest=False)
def add_to_favorite(*args, **kwargs):
	user = frappe.get_value("User", frappe.session.user, ["username", "full_name"], as_dict=True)
	store = kwargs.get("store")
	if not store:
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = "Store is required."
		return
	
	if not frappe.db.exists("Store", store):
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = "Store not found."
		return
	
	if frappe.db.exists("Favorite", user.get("username")):
		doc = frappe.get_doc("Favorite", user.get("username"))
		fav_stores = [row.store for row in doc.stores]
		
		if len(fav_stores) >= 10 and store not in fav_stores:
			frappe.local.response['http_status_code'] = 400
			frappe.local.response['message'] = "Maximum favorite stores limit reached."
			return

		if store in fav_stores:
			doc.stores = [row for row in doc.stores if row.store != store]
			doc.save(ignore_permissions=True)
			frappe.db.commit()
			frappe.local.response['http_status_code'] = 200
			frappe.local.response['message'] = {
				"message": f"Store {store} removed from favorite",
				"data": False
			}
			return
		
		doc.append("stores", {"store": store})
		doc.save(ignore_permissions=True)
		frappe.db.commit()
		frappe.local.response['http_status_code'] = 200
		frappe.local.response['message'] = {
			"message": f"Store {store} added to favorite",
			"data": True
		}
		return

	else:
		fav = frappe.new_doc("Favorite")
		fav.customer = user.get("username")
		fav.append("stores", {"store": store})
		fav.insert(ignore_permissions=True)
		frappe.db.commit()
		frappe.local.response['http_status_code'] = 200
		frappe.local.response['message'] = {
			"message": f"Store {store} added to favorite",
			"data": True
		}



@frappe.whitelist(allow_guest=True)
def search_for_store(*args,**kwargs):
	try:
		if not kwargs.get("search"):
			return get_stores(*args,**kwargs)

		store_search = kwargs.get("search")
		stores = frappe.db.sql("""
			SELECT
				s.name AS id,
				u.full_name AS full_name
			FROM
				`tabStore` AS s
			JOIN
				`tabUser` AS u
			ON
				s.user = u.name
			WHERE
				u.full_name LIKE %s
		""", (f"%{store_search}%",), as_dict=True)
		res = []
		user = frappe.get_value("User",frappe.session.user,["username","full_name"],as_dict=True)

		customer = frappe.get_value("Customer",user.get("username"),'name')

		address = frappe.db.sql(f"""select a.address_line1 , a.latitude , a.longitude from `tabAddress` a join `tabDynamic Link` dl on a.name = dl.parent where a.is_current_location = 1 and dl.link_name = '{customer}'""",as_dict=True)
		if not address:
			address = frappe.db.sql(f"""select a.address_line1 , a.latitude , a.longitude from `tabAddress` a join `tabDynamic Link` dl on a.name = dl.parent where dl.link_name = '{customer}'""",as_dict=True)
		
		
		address = address[-1] if address else None
		
		coordi = [float(address.get("latitude")),float(address.get("longitude"))] if address else [None,None]
		
		for store in stores:
			doc = frappe.get_doc("Store",store.get("id"))

			duration = 0

			if  (doc.pointer_y and  doc.pointer_x) and (coordi[0] and coordi[1]):
				duration = haversine(
					[float(doc.pointer_y or 0), float(doc.pointer_x or 0)], 
					coordi
				)
			
			res.append({
				"id":doc.name,
				"is_favorite":is_favorite(user.get("username") , store.get("id")),
				"cover":doc.store_cover,
				"logo":doc.store_logo,
				"store_name":frappe.get_value("User",doc.user,"full_name"),
				"location":[doc.pointer_y,doc.pointer_x] if doc.pointer_y and doc.pointer_x else []  ,
				"address":doc.address,
				"phone": frappe.get_value("User",doc.user,"mobile_no"),
				"delivery_time":10,
				"menu":frappe.get_list("Menu",{"parent":doc.name},pluck='menu',ignore_permissions=True),
				"duration":f"{round(duration , 2)} KM"
			})
		res = sorted(res, key=lambda x: x['duration'], reverse=False)
		frappe.local.response['http_status_code'] = 200
		frappe.local.response['data'] = res
	except Exception as e:
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = f"An error occurred: {e}"
		frappe.log_error(message=str(e), title=_('Error in search_for_store'))


@frappe.whitelist(allow_guest=False)
def disable_user():
	user = frappe.session.user
	frappe.session.user = "Administrator"
	doc = frappe.get_doc("User",user)
	doc.enabled = 0
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	frappe.local.response['http_status_code'] = 200
	frappe.local.response['message'] = "User Disabled"


def is_favorite(customer , store):
	fav_stores = frappe.get_list("Stores",{"parent":customer},pluck='store',ignore_permissions=True)
	if store in fav_stores:
		return True
	else:
		return False

from datetime import datetime

@frappe.whitelist(allow_guest=False)
def get_order_history(**kwargs):
	status = kwargs.get("status")
	try:
		# Get the phone number of the logged-in user
		phone_number = frappe.get_value("User", frappe.session.user, 'mobile_no')

		if not phone_number:
			frappe.local.response['http_status_code'] = 404
			frappe.local.response['message'] = "User phone number not found."
			return

		# Define base query and parameters
		base_query = """
			SELECT 
				name, 
				creation, 
				status,
				order_type, 
				total_order,
				store,
				delivery,
				invoice,
				reorder as enable_to_reorder ,
				net_delivery_fees as delivery_fees
			FROM 
				`tabOrder` 
			WHERE 
				phone_number = %s
			

		"""
		params = [phone_number]

		order_types = frappe.get_list("Order Type",{"enable":1 , "name":["!=","Delivery"]},['name'])
		

		# Add condition for status if provided
		if status and status.lower() not in ["all", ""]:
			base_query += " AND status = %s"
			params.append(status)

		base_query += " ORDER BY creation DESC ;"

		orders = frappe.db.sql(base_query, params, as_dict=1)
		
		for order in orders:
			delivery = order.get("delivery")
			if delivery :
				order['delivery_number'] = frappe.get_value("User",{"username":delivery},"mobile_no")

			creation_date = order.get('creation')
			if creation_date:
				if isinstance(creation_date, datetime):
					order['creation'] = creation_date.strftime('%Y-%m-%d %H:%M:%S')
				else:
					try:
						order['creation'] = datetime.strptime(creation_date, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
					except ValueError:
						order['creation'] = str(creation_date)

			order_types = frappe.get_list("Store Order Type",{"parent":order.get("store"),"order_type":["!=","Delivery"]},['order_type as id','type','name_in_arabic as ar'],ignore_permissions=True)

			order['reorder'] = []
			if order['enable_to_reorder'] == 0:
				order['reorder'] = order_types



		frappe.local.response['http_status_code'] = 200
		frappe.local.response['orders'] = orders

	except Exception as e:
		frappe.log_error(message=str(e), title=_('Error in get_order_history'))
		frappe.local.response['http_status_code'] = 500
		frappe.local.response['message'] = "An error occurred while fetching order history."



@frappe.whitelist(allow_guest=False)
def get_current_location_delivery(**kwargs):
	order = kwargs.get("order")
	if not order:
		frappe.local.response['http_status_code'] = 500
		frappe.local.response['message'] = _("Please set order")
		return
	
	try:
		delivery = frappe.get_value("Order",order,'delivery')

		if not delivery:
			frappe.local.response['http_status_code'] = 500
			frappe.local.response['message'] = f"""No Delivery assign yet"""
			return

		coordi = [float(frappe.get_value("Delivery",delivery,"pointer_y") or None),float(frappe.get_value("Delivery",delivery,"pointer_x") or None)]

		frappe.local.response['http_status_code'] = 200
		frappe.local.response['coordi'] = coordi

	except Exception as e:
		frappe.local.response['http_status_code'] = 500
		frappe.log_error(message=str(e), title=_('Error in get_order_history'))
		return str(e)
	

@frappe.whitelist(allow_guest=False)
def add_address(**kwargs):
	user = frappe.get_value("User",frappe.session.user,["username","full_name"],as_dict=True)
	if not user:
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = "User not found."
		return

	address = kwargs.get("address")
	latitude = kwargs.get("latitude")
	longitude = kwargs.get("longitude")

	if not address or not latitude or not longitude:
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = "Address is required."
		return

	# if frappe.db.exists("Address",{"parent":user.get("username"),"address":address}):
	# 	frappe.local.response['http_status_code'] = 400
	# 	frappe.local.response['message'] = "Address already exists."
	# 	return

	addr = frappe.new_doc("Address")
	addr.parent = user.get("username")
	addr.city = "Cairo"
	addr.address_line1 = address
	addr.latitude = latitude
	addr.longitude = longitude
	addr.append("links", {
		"link_doctype": "Customer",
		"link_name": user.get("username")
	})
	addr.insert(ignore_permissions=True)
	frappe.db.commit()
	frappe.local.response['http_status_code'] = 200
	frappe.local.response['message'] = "Address added successfully."


@frappe.whitelist(allow_guest=True)
def get_offers(*args,**kwargs):
	user = frappe.get_value("User",frappe.session.user,["username","full_name"],as_dict=True)

	if not kwargs.get("latitude") or not kwargs.get("longitude"):

		customer = frappe.get_value("Customer",user.get("username"),'name')
		address = frappe.db.sql(f"""select a.address_line1 , a.latitude , a.longitude from `tabAddress` a join `tabDynamic Link` dl on a.name = dl.parent where dl.link_name = '{customer}'""",as_dict=True)
		if not address:
			frappe.local.response['http_status_code'] = 400
			frappe.local.response['message'] = "Latitude and Longitude are required."
			return
		
		address = address[-1]
		coordi = [float(address.get("latitude")),float(address.get("longitude"))] 
		print(address)
		print(coordi)
	else:
		
		coordi = [float(kwargs.get("latitude")),float(kwargs.get("longitude"))]
		print(coordi)

	
	try:
		print(coordi)
		zones = search_by_zone(coordi)

		if not zones:
			frappe.local.response['http_status_code'] = 200
			frappe.local.response['message'] = []
			return


		stores = frappe.get_list("Store",{"zone":["in",zones]},pluck="name",ignore_permissions=True)

		offers = frappe.get_list("Offers",{"from":["in",stores],"status":"Active"},['from','offer','descriptions','title'],ignore_permissions=True)

		if not offers:
			frappe.local.response['http_status_code'] = 200
			frappe.local.response['message'] = []
			return

		for store in offers:
			doc = frappe.get_doc("Store",store.get("from"))

			duration = 0

			if  (doc.pointer_y and  doc.pointer_x) and (coordi[0] and coordi[1]):
				duration = haversine(
					[float(doc.pointer_y or 0), float(doc.pointer_x or 0)], 
					coordi
				)
			store['store'] = {
				"id":doc.name,
				"is_favorite":is_favorite(user.get("username") , store.get("id")),
				"cover":doc.store_cover,
				"logo":doc.store_logo,
				"store_name":frappe.get_value("User",doc.user,"full_name"),
				"location":[doc.pointer_y,doc.pointer_x] if doc.pointer_y and doc.pointer_x else []  ,
				"address":doc.address,
				"phone": frappe.get_value("User",doc.user,"mobile_no"),
				"delivery_time":10,
				"menu":frappe.get_list("Menu",{"parent":doc.name},pluck='menu',ignore_permissions=True),
				"duration":f"{round(duration , 2)} KM"
			}

		return offers
	except Exception as e:
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = f"An error occurred: {e}"
		frappe.log_error(message=str(e), title=_('Error in get_offers'))

@frappe.whitelist(allow_guest=False)
def post_reorder():
	files = frappe.request.files
	data = frappe.form_dict
	order = data.get("order")
	if not order:
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = "Order is required."
		return
	
	type = data.get("type")
	if not type:
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = "Type is required."
		return
	
	try:
		
		if type:
			doc = frappe.get_doc("Order",order)
			order = frappe.new_doc("Order")
			
			order.store = doc.store
			order.owner = doc.owner
			order.full_name = doc.full_name
			order.order_type = type
			order.order_reference = doc.name
			order.previous_order_amount = doc.total_order
			order.phone_number = doc.phone_number
			order.address = doc.address
			order.zone_address = doc.zone_address
			order.invoice = doc.invoice
			order.status = "Pending"
			order.order_date = frappe.utils.now_datetime()
			order.note = data.note

			if files:
				for i in files.getlist('order_image'):
					saved_file = download_image(i)
					if saved_file:
						order.append("order_image", {
							"image": saved_file.file_url 
						})
			doc.reorder = 1
			doc.save(ignore_permissions=True)
			order.save(ignore_permissions=True)
			frappe.db.commit()

			frappe.local.response['http_status_code'] = 200
			frappe.local.response['message'] = f"Order Created Successfully."
			return

		else:
			frappe.local.response['http_status_code'] = 400
			frappe.local.response['message'] = f"Please enter a valid type."
			return
	
	except Exception as e:
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = f"An error occurred: {e}"
		frappe.log_error(message=str(e), title=_('Error in post_reorder'))


@frappe.whitelist(allow_guest=False , methods=["POST"])
def make_address_default(**kwargs):
	id = kwargs.get("id")
	if not id:
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = "Address ID is required."
		return
	
	try:
		doc = frappe.get_doc("Address", id)
		doc.flags.ignore_permissions = True
		doc.is_default = 1
		doc.save(ignore_permissions=True)
		frappe.db.commit()
		frappe.local.response['http_status_code'] = 200
		frappe.local.response['message'] = "Address set as default successfully."
	except Exception as e:
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = f"An error occurred: {e}"
		frappe.log_error(message=str(e), title=_('Error in make_address_default'))


@frappe.whitelist(allow_guest=True)
def address(**kwargs):
	id = kwargs.get("id")
	address = kwargs.get("address")
	latitude = kwargs.get("latitude")
	longitude = kwargs.get("longitude")
	is_default = kwargs.get("is_default")
		
	if frappe.request.method == 'GET':
		res = get_address()
	elif frappe.request.method == 'PUT':
		
		res = edit_address(id , address , latitude , longitude , is_default)
	elif frappe.request.method == 'DELETE': 
		res = delete_address(id)
	return res



def delete_address(id):
	try:
		doc = frappe.get_doc("Address" , id )
		doc.delete(ignore_permissions=True)
		frappe.db.commit()
		return "Address Removed"
	except Exception as e:
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = f"An error occurred: {e}"
		frappe.log_error(message=str(e), title=_('Error in delete_address'))

def edit_address(id , address =None, latitude =None,longitude =None , is_default = None):
	try:
		if not id:
			frappe.local.response['http_status_code'] = 400
			frappe.local.response['message'] = "Missing Address ID"
			return "Missing Address ID"
		doc = frappe.get_doc("Address" , id )
		doc.flags.ignore_permissions = True
		
		doc.address_line1 = address if address else doc.address_line1
		doc.latitude = latitude if latitude else doc.latitude
		doc.longitude = longitude if longitude else doc.longitude
		doc.is_default = 1 if is_default else doc.is_default
		doc.save(ignore_permissions=True)
		frappe.db.commit()
		return "Address Updated"

	except Exception as e:
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = f"An error occurred: {e}"
		frappe.log_error(message=str(e), title=_('Error in edit_address'))


def get_address():
	user = frappe.get_value("User",frappe.session.user,["username","full_name"],as_dict=True)

	customer = frappe.get_value("Customer",user.get("username"),'name')
	address = frappe.db.sql(f"""select a.name as id ,a.address_line1 , a.is_default , a.latitude , a.longitude from `tabAddress` a join `tabDynamic Link` dl on a.name = dl.parent where a.is_current_location = 0 and dl.link_name = '{customer}'""",as_dict=True)
	if not address:
		frappe.local.response['http_status_code'] = 200
		frappe.local.response['message'] = []
		return
	return address



@frappe.whitelist(allow_guest=False , methods=["POST"])
def post_current_location():
	user = frappe.get_value("User",frappe.session.user,["username","full_name"],as_dict=True)

	customer = frappe.get_value("Customer",user.get("username"),'name')
	address = frappe.db.sql(f"""select a.name as id , a.address_line1 , a.is_default , a.latitude , a.longitude from `tabAddress` a join `tabDynamic Link` dl on a.name = dl.parent where a.is_current_location = 1 and dl.link_name = '{customer}' ;""",as_dict=True)

	stores = calculate_store_distance(latitude  = frappe.form_dict.get("latitude"), longitude = frappe.form_dict.get("longitude"))
	if not address:
		address_obj = frappe.new_doc("Address")
		address_obj.address_type = "Personal"
		address_obj.address_line1 = "Current Location"
		address_obj.is_current_location = 1
		address_obj.city = "temp"
		address_obj.country = "Egypt"
		address_obj.latitude = frappe.form_dict.get("latitude")
		address_obj.longitude = frappe.form_dict.get("longitude")
		address_obj.distance = []
		address_obj.append("links", {
			"link_doctype": "Customer",
			"link_name": user.get("username")
		})
		# address_obj.distance = stores
		for i in stores:
			address_obj.append("distance", {
				"store": i.get("store"),
				"distance": i.get("distance")
			})
		address_obj.save(ignore_permissions=True)
		frappe.db.commit()
	else:
		address_obj = frappe.get_doc("Address", address[0].get("id"))
		address_obj.latitude = frappe.form_dict.get("latitude")
		address_obj.longitude = frappe.form_dict.get("longitude")
		address_obj.distance = []
		for i in stores:
			address_obj.append("distance", {
				"store": i.get("store"),
				"distance": i.get("distance")
			})
		address_obj.save(ignore_permissions=True)
		frappe.db.commit()
	frappe.local.response['http_status_code'] = 200
	frappe.local.response['message'] = "Current location updated successfully."
	

@frappe.whitelist(allow_guest=False)
def calculate_store_distance(latitude , longitude):
	stores = frappe.get_list("Store",{"status":"Active"},['name','pointer_y','pointer_x'],ignore_permissions=True)
	res = []

	if not stores:
		frappe.local.response['http_status_code'] = 200
		frappe.local.response['message'] = []
		return

	for i in stores:
		if i.pointer_y and i.pointer_x:
			distance = haversine([float(i.pointer_y), float(i.pointer_x)], [float(latitude), float(longitude)])
			res.append({
				"store": i.name,
				"distance": distance
			})
	res = sorted(res, key=lambda x: x['distance'], reverse=False)
	return res
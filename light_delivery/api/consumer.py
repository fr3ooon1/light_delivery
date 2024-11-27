import frappe 
from frappe import _
from frappe.utils import add_to_date, today, nowdate
from frappe.utils import nowdate , get_first_day_of_week , get_first_day ,  get_datetime, now_datetime, time_diff_in_seconds
from datetime import datetime



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
		user = frappe.get_value("User",frappe.session.user,["username","full_name"],as_dict=True)
		
		for store in valid_stores:
			doc = frappe.get_doc("Store",store.get("store"))
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
				"menu":frappe.get_list("Menu",{"parent":doc.name},pluck='menu',ignore_permissions=True)
			})
		
		frappe.local.response['http_status_code'] = 200
		frappe.local.response['message'] = res

	except Exception as e:
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = f"An error occurred: {e}"


@frappe.whitelist(allow_guest=False)
def get_stores(*args,**kwargs):
	idx=0
	tot_stores = frappe.db.count('Store')
	pages = (tot_stores/10)
	if pages%10 > 0:
		pages = int(pages) +1

	if kwargs.get("idx"):
		idx = float(kwargs.get("idx") or 0) -1

	start = idx * 10
	page_length=10
	order_by = "creation desc"

	stores = frappe.db.get_list("Store",['name as id'],order_by=order_by,start=start,page_length=page_length,ignore_permissions=True)
	res = []

	user = frappe.get_value("User",frappe.session.user,["username","full_name"],as_dict=True)
	
	for store in stores:
		doc = frappe.get_doc("Store",store.get("id"))
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
			"menu":frappe.get_list("Menu",{"parent":doc.name},pluck='menu',ignore_permissions=True)
		})
	frappe.local.response['http_status_code'] = 200
	frappe.local.response['data'] = res
	frappe.local.response['message'] = pages


@frappe.whitelist(allow_guest=True)
def get_home_stories():
	try:
		res = []
		stores = frappe.get_list("Store",{"show_in_home":1},['name'],ignore_permissions=True)
		user = frappe.get_value("User",frappe.session.user,["username","full_name","mobile_no"],as_dict=True)
		for store in stores:
			doc = frappe.get_doc("Store",store.get("name"))
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
				"menu":frappe.get_list("Menu",{"parent":doc.name},pluck='menu',ignore_permissions=True)
			})
			frappe.local.response['http_status_code'] = 200
			frappe.local.response['message'] = res
			
	except Exception as e:
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = f"An error occurred: {e}"



@frappe.whitelist(allow_guest=False)
def get_favorite(*args,**kwargs):
	res = []
	user = frappe.get_value("User",frappe.session.user,["username","full_name","mobile_no"],as_dict=True)
	if frappe.db.exists("Favorite",user.get("username")):
		stores = frappe.get_list("Stores",{"parent":user.get("username")},['store'],ignore_permissions=True)
		for store in stores:
			doc = frappe.get_doc("Store",store.get("store"))
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
				"menu":frappe.get_list("Menu",{"parent":doc.name},pluck='menu',ignore_permissions=True)
			})
		return res
	else:
		fav = frappe.new_doc("Favorite")
		fav.customer = user.get("username")
		fav.insert(ignore_permissions=True)
		frappe.db.commit()
		return res
	


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



@frappe.whitelist(allow_guest=False)
def search_for_store(*args,**kwargs):
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
	
	for store in stores:
		doc = frappe.get_doc("Store",store.get("id"))
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
			"menu":frappe.get_list("Menu",{"parent":doc.name},pluck='menu',ignore_permissions=True)
		})
	frappe.local.response['http_status_code'] = 200
	frappe.local.response['data'] = res


# @frappe.whitelist(allow_guest=True)
# def profile

def is_favorite(customer , store):
	fav_stores = frappe.get_list("Stores",{"parent":customer},pluck='store',ignore_permissions=True)
	if store in fav_stores:
		return True
	else:
		return False


@frappe.whitelist(allow_guest=False)
def get_order_history(status = None):
	try:
		phone_number = frappe.get_value("User",frappe.session.user,'mobile_no')



		orders = []

		if status == None or status in ["all","ALL","All"]:
			orders = frappe.get_list("Order" , 
							{
								"phone_number":["LIKE",phone_number]
							} ,
							[
								'name', 
								'creation', 
								'status',
								'order_type', 
								'total_order',
								'store',
								'delivery',
								'invoice'
							])
		else:
			orders = frappe.get_list("Order" ,
							{
								'status':status,
								"phone_number":["LIKE",phone_number]
							} , 
							[
								'name', 
								'creation', 
								'status' , 
								'order_type',
								'total_order',
								'store',
								'delivery',
								'invoice'
							])
		
		
		for order in orders:
			if isinstance(order.get('creation'), datetime):
				order['creation'] = order.get('creation').strftime('%Y-%m-%d %H:%M:%S')
			else:
				order['creation'] = datetime.strptime(order.get('creation'), '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
			

		frappe.local.response['http_status_code'] = 200
		frappe.local.response['orders'] = orders

	except Exception as e:
		frappe.local.response['http_status_code'] = 500
		frappe.log_error(message=str(e), title=_('Error in get_order_history'))
		return str(e)


@frappe.whitelist(allow_guest=False)
def get_current_location_delivery(**kwargs):
	order = kwargs.get("order")
	if not order:
		frappe.local.response['http_status_code'] = 500
		frappe.local.response['message'] = _("Please set order")
		return
	
	try:
		delivery = frappe.get_value("Order",order,'delivery')
		coordi = [frappe.get_value("Delivery",delivery,"pointer_y"),frappe.get_value("Delivery",delivery,"pointer_x")]

		frappe.local.response['http_status_code'] = 200
		frappe.local.response['coordi'] = coordi

	except Exception as e:
		frappe.local.response['http_status_code'] = 500
		frappe.log_error(message=str(e), title=_('Error in get_order_history'))
		return str(e)
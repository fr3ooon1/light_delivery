import frappe 
from frappe import _

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
		stores = frappe.get_list("Store",{"show_in_home":1},['store'],ignore_permissions=True)
		user = frappe.get_value("User",frappe.session.user,["username","full_name","mobile_no"],as_dict=True)
		for store in stores:
			doc = frappe.get_doc("Store",store.get("store"))
			res.append({
				"id":doc.name,
				"is_favorite":is_favorite(user.get("username") , store.get("store")),
				"cover":doc.store_cover,
				"logo":doc.store_logo,
				"store_name":frappe.get_value("User",doc.user,"full_name"),
				"location":[doc.pointer_y,doc.pointer_x] if doc.pointer_y and doc.pointer_x else [],
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



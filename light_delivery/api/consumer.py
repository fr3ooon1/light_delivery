import frappe 
from frappe import _

@frappe.whitelist(allow_guest=False)
def get_stores(*args,**kwargs):
    pass



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
                "location":[doc.pointer_y,doc.pointer_x],
                "phone":user.get("mobile_no"),
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
    res = frappe.get_list("Store",{""})
    pass


def is_favorite(customer , store):
    fav_stores = frappe.get_list("Stores",{"parent":customer},pluck='store',ignore_permissions=True)
    if store in fav_stores:
        return True
    else:
        return False



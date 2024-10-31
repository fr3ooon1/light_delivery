import frappe 
from frappe import _

@frappe.whitelist(allow_guest=True)
def get_stores(*args,**kwargs):
    pass



@frappe.whitelist(allow_guest=True)
def get_favorite(*args,**kwargs):
    res = []
    user = frappe.get_value("User",frappe.session.user,["username","full_name","mobile_no"],as_dict=True)
    if frappe.db.exists("Favorite",user.get("username")):
        stores = frappe.get_list("Stores",{"parent":user.get("username")},['store'],ignore_permissions=True)
        for store in stores:
            doc = frappe.get_doc("Store",store.get("store"))
            res.append({
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
    



@frappe.whitelist(allow_guest=True)
def add_to_favorite(*args,**kwargs):
    user = frappe.get_value("User",frappe.session.user,["username","full_name"],as_dict=True)
    store = kwargs.get("store")
    if frappe.db.exists("Favorite",user.get("username")):
        doc = frappe.get_doc("Favorite",user.get("username"))
        doc.append("stores",{
            "store":store
        })
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        
    else:
        fav = frappe.new_doc("Favorite")
        fav.customer = user.get("username")
        fav.append("stores",{
            "store":store
        })
        fav.insert(ignore_permissions=True)
        frappe.db.commit()
    
    return f"""Store {store} added to the favorite"""


@frappe.whitelist(allow_guest=True)
def search_for_store(*args,**kwargs):
    res = frappe.get_list("Store",{""})
    pass
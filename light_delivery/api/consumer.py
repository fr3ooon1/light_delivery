import frappe 
from frappe import _

@frappe.whitelist(allow_guest=True)
def get_stores(*args,**kwargs):
    pass



@frappe.whitelist(allow_guest=True)
def get_favorite(*args,**kwargs):

    temp = []
    user = frappe.get_value("User",frappe.session.user,["username","full_name"],as_dict=True)
    if frappe.db.exists("Favorite",user.get("username")):
        stores = frappe.get_list("Stores",{"parent":user.get("username")},['store'],ignore_permissions=True)
        for store in stores:
            doc = frappe.get_doc("Store",store.get("store"))
            temp.append({
                "cover":doc.store_cover,
                "logo":doc.store_logo,
                "store_name":frappe.get_value("User",doc.user,"full_name"),
                "location":[doc.pointer_y,doc.pointer_x],
                "phone":"",
                "delivery_time":10,
                "menu":frappe.get_list("Menu",{"parent":user.get("username")},['menu'],ignore_permissions=True)
            })
        return temp
    else:
        return "no"
import frappe
from frappe import _,auth



@frappe.whitelist(allow_guest=True)
def login(usr,pwd):
    try:
        login_manager = frappe.auth.LoginManager()
        login_manager.authenticate(user=usr,pwd=pwd)
        login_manager.post_login()
    except frappe.exceptions.AuthenticationError:
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success_key":0,
            "message":"Baio"
        }
        return
    api_generate = generate_keys(frappe.session.user)
    user = frappe.get_doc('User',frappe.session.user)

    frappe.response["message"] = {
        "success_key":1,
        "message":"Auhentication success",
        "sid":frappe.session.sid,
        "api_key":user.api_key,
        "api_secret":api_generate,
        "username":user.username,
        "email":user.email,
        "first_name":user.first_name
    }        

def generate_keys(user):
    user_details = frappe.get_doc('User',user)
    api_secret = frappe.generate_hash(length=15)
    if not user_details.api_key:
        api_key = frappe.generate_hash(length=15)
        user_details.api_key = api_key
    user_details.api_secret = api_secret
    user_details.save()
    return api_secret

# @frappe.whitelist(allow_guest=True)
# def customer():
#     c = frappe.get_list("Customer",fields=['customer_name','customer_type','customer_group','territory','default_price_list'])
#     return c
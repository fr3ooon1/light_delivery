import frappe
from frappe import _
from frappe import _,auth
from frappe.auth import LoginManager
from frappe.exceptions import AuthenticationError




@frappe.whitelist()
def login(usr, pwd):
    try:
        login_manager = LoginManager()
        login_manager.authenticate(user=usr, pwd=pwd)
        login_manager.post_login()
        
    except frappe.AuthenticationError as e:
        frappe.local.response['http_status_code'] = 401
        return {
            'message': 'Login failed',
            'error': str(e)
        }

    
    api_generate = generate_keys(usr)
    user = frappe.get_doc('User', frappe.session.user)

    frappe.local.response["message"] = {
        "status_code": 200,
        "message": "Authentication success",
        "sid": frappe.session.sid,
        "api_key": api_generate.get('api_key'),
        "api_secret": api_generate.get('api_secret'),
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name
    }     

def generate_keys(user):
    user_details = frappe.get_doc('User', user)
    api_secret = frappe.generate_hash(length=15)

    if not user_details.api_key:
        api_key = frappe.generate_hash(length=15)
        user_details.api_key = api_key
    else:
        api_key = user_details.api_key

    user_details.api_secret = api_secret
    user_details.save()

    return {
        'api_key': api_key,
        'api_secret': api_secret
    }


@frappe.whitelist()
def get_user_permissions(user):
    user_permissions = frappe.get_all('User Permission', filters={'user': user}, fields=['allow', 'for_value'])
    permissions_dict = {}
    for perm in user_permissions:
        if perm['allow'] not in permissions_dict:
            permissions_dict[perm['allow']] = []
        permissions_dict[perm['allow']].append(perm['for_value'])
    return permissions_dict
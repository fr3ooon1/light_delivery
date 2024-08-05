import frappe
from frappe import _

from frappe.core.doctype.user.user import generate_keys



@frappe.whitelist(allow_guest=True)
def login(usr, pwd):
	try:
		login_manager = frappe.auth.LoginManager()
		login_manager.authenticate(user=usr, pwd=pwd)
		login_manager.post_login()
		
	except frappe.exceptions.AuthenticationError as e:
		frappe.local.response['http_status_code'] = 401
		return {
			'message': 'Login failed',
			'error': str(e)
		}

	
	user = frappe.get_doc('User', usr)
	api_secret = generate_keys(user=usr).get('api_secret')
	frappe.db.commit()

	frappe.local.response["message"] = {
		"status_code": 200,
		"message": "Authentication success",
		"sid": frappe.session.sid,
		"api_key": user.api_key,
		"api_secret": api_secret,
		"username": user.username,
		"email": user.email,
		"first_name": user.first_name
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


@frappe.whitelist(allow_guest = True)
def registration (*args , **kwargs):
	if  frappe.db.exists("User",{"phone":kwargs.get("phone"),"email":kwargs.get("email")}):
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = _("Employee With Email And Phone Number Already Exist")
		return
	
	

import frappe
from frappe import _

from frappe.core.doctype.user.user import generate_keys
from light_delivery.api.apis import download_image



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
		"first_name": user.first_name,
		"phone": user.mobile_no
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
	files = frappe.request.files
	data = frappe.form_dict
	if float(data.is_store) == 1:
		if  frappe.db.exists("User",{"phone":kwargs.get("phone"),"email":kwargs.get("email")}):
			frappe.local.response['http_status_code'] = 400
			frappe.local.response['message'] = _("Employee With Email And Phone Number Already Exist")
			return
		try:
			store_logo = download_image(files.get('store_logo'))
			store_cover = download_image(files.get('store_cover'))

			new_user = create_user_if_not_exists(**kwargs)
			login(usr = new_user.email, pwd = kwargs.get('password'))
			store_obj = frappe.new_doc("Store")
			store_obj.store_name = data.store_name
			store_obj.status = "Pending"
			store_obj.user = new_user.name
			store_obj.zone = data.zone
			store_obj.address = data.address
			store_obj.store_category = data.store_category
			store_obj.store_logo = store_logo.file_url
			store_obj.store_cover = store_cover.file_url
			store_obj.insert(ignore_permissions=True)
			store_obj.save(ignore_permissions=True)
			frappe.db.commit()

			contact = frappe.new_doc('Contact')
			contact.first_name = store_obj.store_name
			contact.append('phone_nos',{
				"phone":kwargs.get('phone'),
				"is_primary_mobile_no":1
			})
			contact.append('links',{
				"link_doctype":"Store",
				"link_name":store_obj.name,
				"link_type":store_obj.store_name,
			})
			contact.append('email_ids',{
				"email_id":kwargs.get("email"),
				"is_primary":1
			})
			contact.insert(ignore_permissions=True)
			frappe.db.commit()
			

		except Exception as er:
				frappe.local.response['http_status_code'] = 401
				frappe.local.response['message'] =str(er)
				frappe.local.response['data'] = {"errors" : "Not Completed Data"}
				return
	


@frappe.whitelist(allow_guest=True)
def create_user_if_not_exists(**kwargs):
	"""
	this function will create user and set Store
	
	"""
	if frappe.db.exists("User", kwargs.get('email')):
		return
	new_user = frappe.new_doc("User")
	new_user.update({
			"doctype": "User",
			"send_welcome_email": 0,
			"user_type": "System User",
			"first_name": kwargs.get('store_name'),
			"email": kwargs.get('email'),
			"enabled": 0,
			"phone": kwargs.get('phone'),
			"mobile_no": kwargs.get('phone'),
			"new_password":kwargs.get('password'),
			"roles": [{"role" :"System Manager"}],
		})
		
	new_user.insert(ignore_permissions=True)
	new_user.save(ignore_permissions=True)
	role = frappe.get_doc("Role Profile" , 'Purchase')
	roles = [role.role for role in role.roles]
	new_user.add_roles(*roles)
	new_user.save(ignore_permissions=True)
	frappe.db.commit()
	return new_user
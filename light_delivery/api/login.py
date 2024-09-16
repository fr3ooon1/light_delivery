import frappe
from frappe import _

# from frappe.core.doctype.user.user import generate_keys
from light_delivery.api.apis import download_image
from frappe.utils import nowdate 
import json


@frappe.whitelist(allow_guest=True)
def login(*args,**kwargs):
	try:
		password = kwargs.get('pwd')
		filters = {}

		if kwargs.get("usr"):
			filters = {"username":kwargs.get("usr")}
		elif kwargs.get("phone"):
			filters = {"mobile_no":kwargs.get("phone")}
		elif kwargs.get("email"):
			filters = {"email":kwargs.get("email")}
		else:
			frappe.local.response['http_status_code'] = 401
			return {
				'message': 'Login failed',
			}
		user_obj = frappe.get_doc("User",filters)
		login_manager = frappe.auth.LoginManager()
		login_manager.authenticate(user=user_obj.name, pwd=password)
		login_manager.post_login()
		
			
		
	except frappe.exceptions.AuthenticationError as e:
		frappe.local.response['http_status_code'] = 401
		return {
			'message': 'Login failed',
			'error': str(e)
		}
	store_logo = None
	store_cover = None
	coordi = []
	if frappe.db.exists("Store",{"user":user_obj.name}):
		store = frappe.get_doc("Store",{"user":user_obj.name})
		store_logo = store.store_logo
		store_cover = store.store_cover
		if store.store_location:
			coordi = json.loads(store.store_location)["features"][0]["geometry"].get("coordinates", None)

	api_secret = generate_keys(user=user_obj.name).get('api_secret')
	frappe.db.commit()

	frappe.local.response["message"] = {
		"status_code": 200,
		"message": "Authentication success",
		"sid": frappe.session.sid,
		"api_key": user_obj.api_key,
		"api_secret": api_secret,
		"Auth":f"""token {user_obj.api_key}:{api_secret}""",
		"username": user_obj.username,
		"email": user_obj.email,
		"first_name": user_obj.first_name,
		"phone": user_obj.mobile_no,
		"username":user_obj.username,
		"store_logo":store_logo,
		"store_cover":store_cover,
		"coordination":coordi,
	}     


@frappe.whitelist()
def generate_keys(user):
    """
    Generate API key and secret for the user.
    :param user: Username
    :return: API secret
    """
    user_details = frappe.get_doc("User", user , ignore_permissions=1)
    api_secret = frappe.generate_hash(length=15)

    if not user_details.api_key:
        api_key = frappe.generate_hash(length=15)
        user_details.api_key = api_key
        user_details.save(ignore_permissions=1)
        frappe.db.commit()

    user_details.api_secret = api_secret
    user_details.save()	
    return {"api_secret": api_secret}

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
	if  frappe.db.exists("User",{"phone":kwargs.get("phone"),"email":kwargs.get("email")}):
		frappe.local.response['http_status_code'] = 200
		frappe.local.response['message'] = _("Employee With Email And Phone Number Already Exist")
		return
	try:
		new_user = create_user_if_not_exists(**kwargs)
		login(email = new_user.email, pwd = kwargs.get('password'))

		if float(data.is_store) == 1:
			store_logo = download_image(files.get('store_logo'))
			store_cover = download_image(files.get('store_cover'))
			store_obj = frappe.new_doc("Store")
			store_obj.store_name = data.full_name
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
		else:
			delivery_obj = frappe.new_doc("Delivery")
			# delivery_obj.delivery_category = "gold"
			delivery_obj.national_id = data.national_id
			delivery_obj.delivery_name = data.full_name
			delivery_obj.date_of_joining = nowdate() 
			delivery_obj.status = "Pending"
			delivery_obj.user = new_user.name
			delivery_obj.insert(ignore_permissions=True)
			delivery_obj.save(ignore_permissions=True)
			frappe.db.commit()

		customer_obj = frappe.new_doc("Customer")
		customer_obj.customer_name = store_obj.name if float(data.is_store) == 1 else delivery_obj.name
		customer_obj.insert(ignore_permissions=True)
		customer_obj.save(ignore_permissions=True)
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
		contact.save(ignore_permissions=True)
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
			"username": kwargs.get("store_name").lower().replace(" ","_")+ frappe.generate_hash(length=4),
			"enabled": 1,
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
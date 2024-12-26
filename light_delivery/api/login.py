import frappe
from frappe import _

# from frappe.core.doctype.user.user import generate_keys
from light_delivery.api.apis import download_image
import json
from light_delivery.api.delivery_request import get_balance



@frappe.whitelist(allow_guest=True)
def login(*args,**kwargs):
	try:
		password = kwargs.get('pwd')
		filters = {}
		res = {}

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
		
		if not frappe.db.exists("User",filters):
			frappe.local.response['http_status_code'] = 401
			frappe.local.response["message"] ={
				'message': 'User Not Found',
			}
			return
		
		# user_obj = frappe.get_doc("User",filters)


		user_obj = frappe.db.get_value("User", filters, ["name", "username" , "first_name", "api_key", "notification_key","email","mobile_no"], as_dict=True)
		
		login_manager = frappe.auth.LoginManager()
		login_manager.authenticate(user=user_obj.get("name"), pwd=password)
		login_manager.post_login()


		
		
			
		
	except frappe.exceptions.AuthenticationError as e:
		frappe.local.response['http_status_code'] = 401
		return {
			'message': 'Wronge Password',
			'error': str(e)
		}

	coordi = []
	api_secret = generate_keys(user=user_obj.get("name") ,  notification_key=kwargs.get("notification_key")).get('api_secret')
	res = {
		"status_code": 200,
		"message": "Authentication success",
		"sid": frappe.session.sid,
		"api_key": user_obj.get("api_key"),
		"api_secret": api_secret,
		"Auth":f"""token {user_obj.get("api_key")}:{api_secret}""",
		"username": user_obj.get("username"),
		"email": user_obj.get("email"),
		"first_name": user_obj.get("first_name"),
		"phone": user_obj.get("mobile_no"),
		"notification_key":kwargs.get("notification_key") if kwargs.get("notification_key") else user_obj.get("notification_key"),
	}

	if frappe.db.exists("Store",{"user":user_obj.name}):
		store = frappe.get_value("Store",{"user":user_obj.name},['name','store_location','store_logo','store_cover'],as_dict=True)
		res['store_logo'] = frappe.get_value("Store",{"user":frappe.session.user},"store_logo")
		res['store_cover'] = frappe.get_value("Store",{"user":frappe.session.user},"store_cover")
		if store.get("store_location"):
			coordi = json.loads(frappe.get_value("Store",{"user":frappe.session.user},"store_location"))["features"][0]["geometry"].get("coordinates", None)
			res['coordination'] = coordi if coordi else None
		else:
			res['coordination'] = []
	
	if frappe.db.exists("Delivery",{"user":frappe.session.user}):
		res['cash'] =frappe.get_value("Delivery",{"user":frappe.session.user},"cash") 
		status = frappe.get_value("Delivery",{"user":frappe.session.user},"status") 
		if status in ['Hold','Offline','Pending']:
			status = "Offline"
		else:
			status = "Online"
		res["status"]=  status


	res['wallet'] = float(get_balance(user_obj.first_name) or 0)


		

	
	frappe.db.commit()
	frappe.local.response["message"] = res


@frappe.whitelist()
def generate_keys(user , notification_key):
	"""
	Generate API key and secret for the user.
	:param user: Username
	:return: API secret
	"""
	# user_details = frappe.get_doc("User", user , ignore_permissions=1)
	api_secret = frappe.generate_hash(length=15)

	user = frappe.get_value("User", user , ["api_key", "notification_key"], as_dict=True)

	if notification_key:
		frappe.db.set_value("User", user, "notification_key", notification_key)

	if not user.get("api_key"):
		api_key = frappe.generate_hash(length=15)
		frappe.db.set_value("User", user, "api_key", api_key)


	user_obj = frappe.get_doc("User", user)
	user_obj.api_secret = api_secret
	user_obj.save(ignore_permissions=True)
	# frappe.db.set_value("User", user, "api_secret", api_secret)
	frappe.db.commit()
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
	if  frappe.db.exists("User",{"email":kwargs.get("email")}) or frappe.db.exists("User",{"phone":kwargs.get("phone")}):
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = _("User With Email or Phone Number Already Exist")
		return _("User With Email And Phone Number Already Exist")
	try:
		new_user = create_user_if_not_exists(**kwargs)
		login(email = new_user.email, pwd = kwargs.get('password'))


		store_obj = {}
		delivery_obj = {}
		customer_group = None
		customer_name = None



		if float(data.is_store) == 1:
			
			store_obj = frappe.new_doc("Store")
			store_obj.store_name = data.store_name
			store_obj.status = "Pending"
			store_obj.user = new_user.name
			store_obj.zone = data.zone
			store_obj.address = data.address
			store_obj.store_category = data.store_category

			if files.get('store_logo'):
				store_logo = download_image(files.get('store_logo'))
				store_obj.store_logo = store_logo.file_url

			if files.get('store_cover'):
				store_cover = download_image(files.get('store_cover'))
				store_obj.store_cover = store_cover.file_url
				
			store_obj.name = new_user.name
			store_obj.username = new_user.username
			store_obj.pointer_y = data.late
			store_obj.pointer_x = data.lng
			store_obj.insert(ignore_permissions=True)
			customer_group = "Store"
			customer_name = store_obj.name
		elif float(data.is_store) == 0:
			delivery_obj = frappe.new_doc("Delivery")
			delivery_obj.national_id = data.national_id
			delivery_obj.delivery_name = data.full_name
			delivery_obj.date_of_joining = frappe.utils.nowdate() 
			delivery_obj.status = "Pending"
			delivery_obj.user = new_user.name
			delivery_obj.username = new_user.username
			delivery_obj.insert(ignore_permissions=True)
			customer_group = "Delivery"
			customer_name = delivery_obj.name
		elif float(data.is_store) == 2:
			customer_name = new_user.username
			customer_group = "Consumer"

			

		if float(data.is_store) != 0:
			customer_obj = frappe.new_doc("Customer")
			customer_obj.customer_name = customer_name
			customer_obj.customer_group = customer_group
			customer_obj.insert(ignore_permissions=True)
			customer_obj.save(ignore_permissions=True)
			frappe.db.commit()
			create_address( new_user.username , data.address , data.latitude , data.longitude)
			contact = frappe.new_doc('Contact')
			contact.first_name = store_obj.store_name if store_obj else data.full_name
			contact.append('phone_nos',{
				"phone":kwargs.get('phone'),
				"is_primary_mobile_no":1
			})
			contact.append('links',{
				"link_doctype":"Customer" ,
				"link_name":customer_obj.name , 
				"link_type":customer_obj.name
			})
			contact.append('email_ids',{
				"email_id":kwargs.get("email"),
				"is_primary":1
			})
			contact.insert(ignore_permissions=True)
			contact.save(ignore_permissions=True)
		else:
			supplier = frappe.new_doc("Supplier")
			supplier.supplier_name = data.full_name
			supplier.supplier_type = "Individual"
			supplier.insert(ignore_permissions=True)

			contact = frappe.new_doc('Contact')
			contact.first_name = data.full_name
			contact.append('phone_nos',{
				"phone":kwargs.get('phone'),
				"is_primary_mobile_no":1
			})
			contact.append('links',{
				"link_doctype":"Supplier" ,
				"link_name":supplier.name , 
				"link_type":supplier.name
			})
			contact.append('email_ids',{
				"email_id":kwargs.get("email"),
				"is_primary":1
			})
			contact.insert(ignore_permissions=True)
			contact.save(ignore_permissions=True)


		frappe.db.commit()
		

	except frappe.DuplicateEntryError:
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = _("A user with this email already exists.")
	except frappe.ValidationError as e:
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = str(e)
	except Exception as e:
		frappe.local.response['http_status_code'] = 500
		frappe.local.response['message'] = _("An unexpected error occurred: {0}").format(str(e))

def create_address(user , address , latitude , longitude):
	if not address:
		return True
	doc = frappe.new_doc("Address")
	doc.address_line1 = address
	doc.latitude = latitude
	doc.longitude = longitude
	doc.address_type = "Personal"
	doc.city = "Cairo"
	doc.append('links',{
			"link_doctype":"Customer" ,
			"link_name":user , 
			"link_type":user
		})
	doc.insert(ignore_permissions=True)

	fav = frappe.new_doc("Favorite")
	fav.customer = user
	fav.insert(ignore_permissions=True)
	
	frappe.db.commit()

@frappe.whitelist(allow_guest=True)
def create_user_if_not_exists(**kwargs):
	"""
	This function will create a user and set Store.
	"""
	try:
		if frappe.db.exists("User", kwargs.get('email')):
			frappe.local.response['http_status_code'] = 400
			frappe.local.response['message'] = _("The email already exists")
			return _("The email already exists")

		new_user = frappe.new_doc("User")
		user_name = None
		if kwargs.get('store_name'):
			user_name = kwargs.get("store_name").lower().replace(" ", "_") + frappe.generate_hash(length=4)
		else:
			user_name = kwargs.get('full_name').lower().replace(" ", "_") + frappe.generate_hash(length=4)

		new_user.update({
			"doctype": "User",
			"send_welcome_email": 0,
			"user_type": "System User",
			"first_name": kwargs.get('store_name') if kwargs.get('store_name') else kwargs.get('full_name'),
			"email": kwargs.get('email'),
			"username": user_name,
			"enabled": 1,
			"phone": kwargs.get('phone'),
			"mobile_no": kwargs.get('phone'),
			"new_password": kwargs.get('password'),
			"roles": [{"role": "System Manager"}],
		})

		new_user.insert(ignore_permissions=True)

		role = frappe.get_doc("Role Profile", 'Purchase')
		roles = [role.role for role in role.roles]
		new_user.add_roles(*roles)

		new_user.save(ignore_permissions=True)
		frappe.db.commit()

		return new_user

	except frappe.DuplicateEntryError:
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = _("A user with this email already exists.")
		return _("A user with this email already exists.")
	except frappe.ValidationError as e:
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = str(e)
		return _(str(e))
	except Exception as e:
		# Catch any other exceptions and return a 500 error
		frappe.local.response['http_status_code'] = 500
		frappe.local.response['message'] = _("An unexpected error occurred: {0}").format(str(e))
		return _("An unexpected error occurred: {0}").format(str(e))
		# frappe.log_error(frappe.get_traceback(), _("User Creation Error"))


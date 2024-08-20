import frappe
from frappe import _
from frappe.utils.password import check_password
from light_delivery.api import login


"""
1-get forget pass request with email or phone
2-get pass and repass  and reset pass 
3-then make login
"""


@frappe.whitelist(allow_guest=True)
def ask_for_forget_password(**kwargs):
	conditions = ' 1=1 '
	if kwargs.get("phone"):
		conditions += " AND `tabUser`.phone= '%s' "%kwargs.get("phone")
	if kwargs.get("email"):
		conditions += " AND `tabUser`.email= '%s' "%kwargs.get("email")
	sql = f"""
		SELECT name,email FROM `tabUser` WHERE {conditions}
	"""
	user_data = frappe.db.sql(sql,as_dict=1)
	if not len(user_data):
		frappe.local.response['http_status_code'] = 400
		frappe.response["message"] =_("Not User For This Creditintals")
		return
	new_reset_pass_doc = frappe.new_doc('Reset Password')
	new_reset_pass_doc.update({
		'user':user_data[0].get("name")
	})
	new_reset_pass_doc.insert(ignore_permissions=True)
	frappe.db.commit()
	frappe.local.response['http_status_code'] = 200
	frappe.local.response["message"] = _("Password reset request Created")
	frappe.local.response["data"] = {
		"name" : new_reset_pass_doc.name , "code" : new_reset_pass_doc.name
	}

	return



@frappe.whitelist(allow_guest=True)
def validate_reset_request(**kwargs):
	try:
		code=kwargs.get('code')
		rest_pass_doc = frappe.get_doc('Reset Password',code)
		frappe.local.response['http_status_code'] = 200
		frappe.local.response["message"] = _("Valid Code")
		frappe.local.response["data"] = {
			"code" :code
		}

		return 
	except Exception as er:
		frappe.local.response['http_status_code'] = 400
		frappe.response["message"] =_(f"{er}")

		
		return 
@frappe.whitelist(allow_guest=True)
def reset_password(**kwargs):
	code=kwargs.get('code')
	password=kwargs.get('password')
	repeat_password=kwargs.get('repeat_password')
	rest_pass_doc = frappe.get_doc('Reset Password',code)
	if not rest_pass_doc or (password != repeat_password) or rest_pass_doc.docstatus == 1:
		frappe.local.response['http_status_code'] = 400
		frappe.response["message"] =_("Wrong Code or Password Not Match")
		return 
	try:
		user = frappe.get_doc('User',rest_pass_doc.user)
		user.new_password = password
		user.save(ignore_permissions=True)
		frappe.db.commit()
		rest_pass_doc.password = password
		rest_pass_doc.repeat_password = repeat_password
		rest_pass_doc.status= 'Valid'
		rest_pass_doc.save(ignore_permissions=True)
		rest_pass_doc.submit()
		frappe.db.commit()
		close_other_reset_pass_doc(user.name)
		# login("mohamed.essam68.me@gmail.com", "MoHany@1234")
		frappe.local.response['http_status_code'] = 200
		frappe.response["message"] =_(f"Password Changed")
	except Exception as er:
		frappe.local.response['http_status_code'] = 400
		frappe.response["message"] =_(f"Password Not Valid")
		frappe.response["data"] = {
			"error" : f"{er}"
		}

		return

def respose_info(**kwargs):
	frappe.local.response.update(kwargs)

	return

def close_other_reset_pass_doc(user):
	frappe.db.sql(f"""
	Update `tabReset Password` Set docstatus=1 , status='Invalid' WHERE user='{user}' AND docstatus=0
	""")
	frappe.db.commit()
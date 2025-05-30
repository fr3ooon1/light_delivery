import frappe
from frappe import _
from frappe.utils.password import check_password
from light_delivery.api import login
import requests
import json
import random
from frappe.utils import now, get_datetime
from datetime import timedelta


@frappe.whitelist(allow_guest=True)
def ask_for_forget_password(**kwargs):
	conditions = ' 1=1 '
	if kwargs.get("username"):
		conditions += " AND `tabUser`.username= '%s' "%kwargs.get("username")
	elif kwargs.get("mobile_no"):
		conditions += " AND `tabUser`.mobile_no= '%s' "%kwargs.get("mobile_no")
	elif kwargs.get("email"):
		conditions += " AND `tabUser`.email= '%s' "%kwargs.get("email")
	sql = f"""
		SELECT name,email,mobile_no,full_name FROM `tabUser` WHERE {conditions}
	"""
	user_data = frappe.db.sql(sql,as_dict=1)
	if not len(user_data):
		frappe.local.response['http_status_code'] = 400
		frappe.response["message"] =_("Not User For This Creditintals")
		return
	
	

	else:
		try:
			
			setting = frappe.get_doc("Deductions")
			otp = random.randint(100000, 999999)
			user = user_data[0]
			message = f"""
			استاذ {user.get("full_name")}
			كلمة مرور لمرة واحدة:  {otp}
			يرجى استخدام كلمة المرور لمرة واحدة لتسجيل الدخول إلى حسابك.
			"""
			user_full_name = user.get("full_name")
			message = (
				f"استاذ {user_full_name}\n"
				f"كلمة مرور لمرة واحدة: {otp}\n"
				"يرجى استخدام كلمة المرور لمرة واحدة لتسجيل الدخول إلى حسابك."
			)


			url = f"""{setting.url}?username={setting.username}&password={setting.password}&sendername={setting.sendername}&message={message}&mobiles={user.get("mobile_no")}"""

			payload = {}
			headers = {}

			response = requests.request("GET", url, headers=headers, data=payload)
			if response.status_code == 200:
				doc = frappe.new_doc("Reset Password")
				doc.user = user.get("name")
				doc.otp = otp
				now_time = get_datetime(now())
				new_time = now_time + timedelta(minutes=5)
				doc.validate_to = new_time
				doc.save(ignore_permissions=True)
				frappe.db.commit()
				frappe.local.response['http_status_code'] = 200
				frappe.response["message"] = _("Code Sent To Your Mobile")
			else:
				frappe.local.response['http_status_code'] = 400
				frappe.response["message"] = _("Error In Sending Code")

		except Exception as er:
			frappe.local.response['http_status_code'] = 400
			frappe.response["message"] = er
			




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

	# user = frappe.session.user

	conditions = ' 1=1 '
	if kwargs.get("username"):
		conditions += " AND `tabUser`.username= '%s' "%kwargs.get("username")
	elif kwargs.get("mobile_no"):
		conditions += " AND `tabUser`.mobile_no= '%s' "%kwargs.get("mobile_no")
	elif kwargs.get("email"):
		conditions += " AND `tabUser`.email= '%s' "%kwargs.get("email")
	sql = f"""
		SELECT name,email,mobile_no,full_name FROM `tabUser` WHERE {conditions}
	"""
	user_data = frappe.db.sql(sql,as_dict=1)
	if not len(user_data):
		frappe.local.response['http_status_code'] = 400
		frappe.response["message"] =_("Not User For This Creditintals")
		return
	

	new_password = kwargs.get("password") 
	user = user_data[0]

	otp = kwargs.get("otp")

	if not otp:
		frappe.local.response['http_status_code'] = 400
		frappe.response["message"] =_("Code Not Found")
		return
	
	rest_pass_doc = frappe.get_last_doc('Reset Password',{"user":user.get("name") , "status":["in",["","Invalid",None]]})

	if rest_pass_doc.otp != otp:
		frappe.local.response['http_status_code'] = 400
		frappe.response["message"] =_("Code Not Corect")
		return

	if get_datetime(now()) > rest_pass_doc.validate_to:
		frappe.local.response['http_status_code'] = 400
		frappe.response["message"] =_("Code Expired")
		return


	try:

		user_doc = frappe.get_doc("User", user)
		user_doc.new_password = new_password
		rest_pass_doc.status = "Valid"
		rest_pass_doc.save(ignore_permissions=True)
		user_doc.save(ignore_permissions=True)
		

		frappe.db.commit()
		frappe.local.response['http_status_code'] = 200
		frappe.response["message"] = _("Password Changed")
	
	except Exception as e:

		frappe.local.response['http_status_code'] = 400
		frappe.response["message"] = _(e)
		return

def respose_info(**kwargs):
	frappe.local.response.update(kwargs)

	return

def close_other_reset_pass_doc(user):
	frappe.db.sql(f"""
	Update `tabReset Password` Set docstatus=1 , status='Invalid' WHERE user='{user}' AND docstatus=0
	""")
	frappe.db.commit()


@frappe.whitelist(allow_guest=False)
def change_password(*args, **kwargs):

	user = frappe.session.user
	old_password = kwargs.get("old_password")
	new_password = kwargs.get("new_password") 

	try:

		check_password(user, old_password)


		user_doc = frappe.get_doc("User", user)
		user_doc.new_password = new_password
		user_doc.save(ignore_permissions=True)
		

		frappe.db.commit()
		frappe.local.response['http_status_code'] = 200
		frappe.response["message"] = _("Password Changed")
	
	except Exception as e:

		frappe.local.response['http_status_code'] = 400
		frappe.response["message"] = _(e)
		# frappe.response["message"] = {
		# 	"error": str(e)
		# }


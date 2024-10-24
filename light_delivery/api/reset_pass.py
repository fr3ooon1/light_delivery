import frappe
from frappe import _
from frappe.utils.password import check_password
from light_delivery.api import login
import requests
import json


"""
1-get forget pass request with email or phone
2-get pass and repass  and reset pass 
3-then make login


https://smssmartegypt.com/sms/api/?username=H18dl27&password=CXbIU%3CDEYF1Q&sendername=Dynamic&mobiles=01022750334&message=hello
"""


@frappe.whitelist(allow_guest=True)
def ask_for_forget_password(**kwargs):
	conditions = ' 1=1 '
	if kwargs.get("username"):
		conditions += " AND `tabUser`.username= '%s' "%kwargs.get("username")
	elif kwargs.get("phone"):
		conditions += " AND `tabUser`.phone= '%s' "%kwargs.get("phone")
	elif kwargs.get("email"):
		conditions += " AND `tabUser`.email= '%s' "%kwargs.get("email")
	sql = f"""
		SELECT name,email,mobile_no FROM `tabUser` WHERE {conditions}
	"""
	user_data = frappe.db.sql(sql,as_dict=1)
	if not len(user_data):
		frappe.local.response['http_status_code'] = 400
		frappe.response["message"] =_("Not User For This Creditintals")
		return
	else:
		try:
			code = kwargs.get('code')
			signature = kwargs.get('signature')

			mobile_no = int(user_data[0].get("mobile_no"))
			# print(type(user_data[0].get("mobile_no")))

			sms_obj = frappe.get_doc("Light Integration")
			sms_url = sms_obj.sms_url
			username = sms_obj.username
			password = sms_obj.password
			sendername = sms_obj.sendername
			message = f"""Welcome to Dynamic\n your code: {code}\n app signature is : {signature}"""

			# t = sms_obj
			# mobile = "01141122335"
			# mobile_no = "0"+str(mobile_no)
			# print(mobile_no, mobile)
			# print(mobile_no is mobile)
			# print(mobile_no == mobile)
			# print(type(mobile_no),type(mobile))

			params = {
				"username": username, 
				"password": password,
				"sendername": sendername,
				"mobiles": mobile_no,
				"message": message,
			}

			r = requests.get(f"""https://smssmartegypt.com/sms/api/?username={username}&password={password}&sendername={sendername}&mobiles={mobile_no}&message={message}""")
			frappe.local.response['http_status_code'] = 200
			frappe.local.response["message"] = _("Message Sent")
			frappe.response["data"] = r.json()
			return 
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

	password=kwargs.get('password')

	try:
		user = frappe.get_doc('User',{"username":kwargs.get('username')})
		user.new_password = password
		user.save(ignore_permissions=True)
		frappe.db.commit()

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


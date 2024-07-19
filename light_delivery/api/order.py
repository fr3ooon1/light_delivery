import frappe
from frappe import _
import requests
from light_delivery.utils import validate_token
 

@frappe.whitelist(allow_guest=True)
def get_orders(user=None):
    # Validate the token
    # print("Hello")
    # validate_token()
	# url = "http://frappe.local:8000/api/method/frappe.auth.get_logged_user"
	# headers = {
    # 	'Authorization': "token <api_key>:<api_secret>"
	# }
	# response = requests.request("GET", url, headers=headers)
    
    if not user:
        user = "administrator"

    try:
        # Check if the user has the required role
        roles = frappe.get_roles(user)
        if 'Accounts User' in roles:
            # Get all orders with specific fields
            all_orders = frappe.get_list("Order", fields=['name', 'full_name', 'phone_number', 'address', 'invoice'])

            for order in all_orders:
                invoice = order.get("invoice")
                if invoice:
                    file = frappe.get_doc("File", {"file_url": invoice})
                    order['file'] = "http://84.247.182.89:81"+file.file_url

            # Construct response
            res = {}
            if all_orders:
                res = {
                    'status_code': 200,
                    'message': _('All Orders'),
                    'data': all_orders
                }
            else:
                res = {
                    'status_code': 204,
                    'message': _('No Orders Found'),
                    'data': all_orders
                }
            return res
        else:
            return {
                'status_code': 403,
                'message': _('User does not have the required role'),
            }

    except Exception as e:
        frappe.log_error(message=str(e), title=_('Error in get_orders'))
        frappe.local.response['http_status_code'] = 500
        res = {
            "status_code": 500,
            "message": str(e)
        }
        return res


	
@frappe.whitelist()
def get_order(user , order):
	try:
		roles = frappe.get_roles(user)
		if 'Accounts User' in roles:
			order = frappe.get_list("Order" , filters =  {'name':order} , fields = ['*'])
			res = {}
			if order:
				res = {
					'status_code' : 200 ,
					'message' : _('All data of Order') ,
					'data' : order
				}
				return res
			else:
				res = {
					'status_code' : 204 ,
					'message' : _('No Order Found'),
					'data' : order
				}
				return res
		else:
			return {
				'status_code': 403,
				'message': _('User does not have the required role'),
			}
	except Exception as e:
		frappe.log_error(message=str(e), title=_('Error in get_order'))
		frappe.local.response['http_status_code'] = 500
		res = {
			"status_code": 500,
			"message": str(e)
		}
		return res
	
@frappe.whitelist()
def get_order_type():
	try:
		order_type = frappe.get_list("Order Type" , pluck ='name')
		res = {}
		if order_type:
			res = {
				'status_code' : 200 ,
				'message' : _('All data of Order Types') ,
				'data' : order_type
			}
			return res
		else:
			res = {
				'status_code' : 204 ,
				'message' : _('No Order Type Found'),
				'data' : order_type
			}
			return res
		
	except Exception as e:
		frappe.log_error(message=str(e), title=_('Error in get_order_type'))
		frappe.local.response['http_status_code'] = 500
		res = {
			"status_code": 500,
			"message": str(e)
		}
		return res
	
@frappe.whitelist()
def get_zone_address():
	try:
		zone_addres = frappe.get_list("Zone Address" , pluck ='name')
		res = {}
		if zone_addres:
			res = {
				'status_code' : 200 ,
				'message' : _('All data of Zone Address') ,
				'data' : zone_addres
			}
			return res
		else:
			res = {
				'status_code' : 204 ,
				'message' : _('No zone address Type Found'),
				'data' : zone_addres
			}
			return res
		
	except Exception as e:
		frappe.log_error(message=str(e), title=_('Error in get_zone_address'))
		frappe.local.response['http_status_code'] = 500
		res = {
			"status_code": 500,
			"message": str(e)
		}
		return res





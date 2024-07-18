import frappe
from frappe import _
import requests


@frappe.whitelist()
def get_orders(user=None):
    # Validate the token
    validate_token()
    
    if not user:
        user = frappe.session.user

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
                    order['file'] = file

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


from frappe.utils import get_request_header

def validate_token():
    token = get_request_header("Authorization", "").split("Bearer ")[-1]
    
    if not token:
        frappe.throw(_("Missing token"), frappe.AuthenticationError)
    
    # Assuming you are using JWT for tokens
    try:
        decoded_token = frappe.jwt.decode(token, frappe.conf.secret)
    except Exception:
        frappe.throw(_("Invalid token"), frappe.AuthenticationError)
    
    user = decoded_token.get("user")
    
    if not user:
        frappe.throw(_("Invalid token"), frappe.AuthenticationError)
    
    # Ensure user is active
    user_doc = frappe.get_doc("User", user)
    if not user_doc.enabled:
        frappe.throw(_("User is disabled"), frappe.AuthenticationError)
    
    # Set the user for the current request
    frappe.set_user(user)

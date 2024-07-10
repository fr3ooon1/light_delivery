import frappe
from frappe import _
import requests


@frappe.whitelist()
def get_orders(user , api_token = None):
    try:
        headers = {"Authorization": f"token {api_token}"}
        # user_response = requests.get(headers=headers)
        roles = frappe.get_roles(user)
        if 'Accounts User' in roles:
            all_orders = frappe.get_list("Order" , fields = ['name' , 'full_name' , 'phone_number' , 'address' , 'invoice'])
            res = {}
            if all_orders:
                res = {
                    'status_code' : 200 ,
                    'message' : _('All Orders') ,
                    'data' : all_orders
                }
                return res
            else:
                res = {
                    'status_code' : 204 ,
                    'message' : _('No Orders Found'),
                    'data' : all_orders
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
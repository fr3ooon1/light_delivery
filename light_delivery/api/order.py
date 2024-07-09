import frappe
from frappe import _


@frappe.whitelist()
def get_orders(user =None):
    try:
        roles = frappe.get_roles(user)
        if 'Accounts User' in roles:
            all_orders = frappe.get_list("Order" , pluck = 'name')
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
        res = {
            "status_code": 500,
            "message": str(e)
        }
        return res
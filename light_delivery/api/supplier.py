import frappe
from frappe import _
from light_delivery.api.login import get_user_permissions

@frappe.whitelist()
def create_supplier(user = None , supplier_name = None):
    doc = frappe.new_doc("Supplier")
    doc.supplier_name = supplier_name
    


@frappe.whitelist()
def get_all_suppliers(user = None):
    if not user:
        user = frappe.session.user

    try:
        roles = frappe.get_roles(user)
        if 'Accounts User' in roles:
            all_suppliers = frappe.get_list("Supplier" , filters = {"disabled" : 0} , pluck = 'name')
            res = {}
            if all_suppliers:
                res = {
                    'status_code' : 200 ,
                    'message' : _('All Suppliers') ,
                    'data' : all_suppliers
                }
                return res
            else:
                res = {
                    'status_code' : 204 ,
                    'message' : _('No Supplier Found'),
                    'data' : all_suppliers
                }
                return res
        else:
            return {
                'status_code': 403,
                'message': _('User does not have the required role'),
            }
    except Exception as e:
        frappe.log_error(message=str(e), title=_('Error in get_all_suppliers'))
        res = {
            "status_code": 500,
            "message": str(e)
        }
        return res





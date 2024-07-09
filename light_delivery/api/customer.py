import frappe
from frappe import _

@frappe.whitelist()
def get_all_customers(user = None):
    
    try:
        user = frappe.session.user
        all_customers = frappe.get_list("Customer",filters = {"disabled" : 0} ,fields=['customer_name','customer_type','customer_group','territory','default_price_list'])
        res = {}
        if all_customers:
            res = {
                'status_code' : 200 ,
                'message' : 'All Customers' ,
                'data' : all_customers
            }
            return res
        else:
            res = {
                'status_code' : 500 ,
                'message' : 'No Customers Found',
                'data' : all_customers
            }
            return res
    except Exception as e:
        res = {
            "status_code": 404,
            "message": str(e)
        }
        return res
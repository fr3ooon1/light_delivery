import frappe
from frappe import _

@frappe.whitelist(allow_guest = True)
def get_invoices():
	try:
		sales_invoice = frappe.get_list("Sales Invoice" , fields = ['*'])
		res = {}
		if sales_invoice:
			res = {
				'status_code' : 200 ,
				'message' : _('All Orders') ,
				'data' : sales_invoice
			}
			return res
		else:
			res = {
				'status_code' : 204 ,
				'message' : _('No Orders Found'),
				'data' : sales_invoice
			}
			return res
	except Exception as e:
		frappe.log_error(message=str(e), title=_('Error in get_invoices'))
		frappe.local.response['http_status_code'] = 500
		res = {
			"status_code": 500,
			"message": str(e)
		}
		return res
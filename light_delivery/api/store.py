import frappe
from frappe import _

@frappe.whitelist(allow_guest = 1)
def get_category():
	categories = frappe.get_list("Store Category" , fields = ['name' , 'category_name_in_arabic'])
	res = {}
	try:
		if categories:
			res = {
					'status_code': 200,
					'message': _('All Categories'),
					'data': categories
				}
		else:
			res = {
					'status_code': 204,
					'message': _('No Orders Found'),
					'data': categories
				}

		return res


	except Exception as e:
		frappe.log_error(message=str(e), title=_('Error in get_category'))
		frappe.local.response['http_status_code'] = 500
		res = {
			"status_code": 500,
			"message": str(e)
		}
		return res
	
import frappe
from frappe import _

@frappe.whitelist(allow_guest = 1)
def get_category():
	sql = """
			SELECT
				name as id,
				category_name as en,
				category_name_in_arabic as ar
			FROM
				`tabStore Category`
		"""
	categories = frappe.db.sql(sql,as_dict =1)
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
					'message': _('No Categories Found'),
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
	
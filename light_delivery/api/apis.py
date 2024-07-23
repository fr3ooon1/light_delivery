import frappe
from frappe import _


@frappe.whitelist(allow_guest=True)
def get_store_state(user=None):
	if not user:
		user = "administrator"
	try:
		roles = frappe.get_roles(user)
		if 'Accounts User' in roles:
			
			"""
			Pending
            Active
            Inactive
			"""

			pending = frappe.db.count('Store', {'status': 'Pending'})
			active = frappe.db.count('Store', {'status': 'Active'})
			inactive = frappe.db.count('Store', {'status': 'Inactive'})
			all_stores = frappe.db.count('Store')


			frappe.local.response['http_status_code'] = 200
			return {
				'status_code': 200,
				'message': _('Count of order status'),
				'data': {
					'pending': pending,
					'active': active,
					'inactive': inactive,
					'all_stores': all_stores
				}
			}
		else:
			frappe.local.response['http_status_code'] = 403
			return {
				'status_code': 403,
				'message': _('User does not have the required role'),
				'data': []
			}
	except Exception as e:
		frappe.log_error(message=str(e), title=_('Error in get_store_state'))
		return {
			"status_code": 500,
			"message": str(e)
		}
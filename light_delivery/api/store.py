import frappe
from frappe import _
from light_delivery.api.delivery_request import calculate_balane

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
	
@frappe.whitelist(allow_guest = 0 )
def get_price_list_for_store():
	sql = f"select store_name ,minimum_price , rate_of_km from `tabStore` where user = '{frappe.session.user}' "
	store = frappe.db.sql(sql , as_dict = 1)
	return store 
	


@frappe.whitelist(allow_guest=False)
def get_pending_requst(*args,**kwargs):
	store = frappe.get_value("Store",{"user":frappe.session.user})
	requests = frappe.get_list("Request Delivery",{"store":store , "status":"Pending"},['name','number_of_order'])
	return requests



@frappe.whitelist(allow_guest=True)
def get_wallet():
	store = frappe.get_value("Store",{"user":frappe.session.user},"name")
	sql = f"""
			select
				*
			from 
				`tabTransactions`
			where
				party_type = '{store}'
				AND paid = 0
	"""

	transactions = frappe.db.sql(sql,as_dict=True)
	balance = calculate_balane(store)

	frappe.local.response['http_status_code'] = 200
	frappe.local.response['transactions'] = transactions
	frappe.local.response['balance'] = float(balance or 0)


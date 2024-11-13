import frappe
from frappe import _
from light_delivery.api.delivery_request import get_balance

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
	try:
		store = frappe.get_value("User",frappe.session.user,["username","first_name"],as_dict=1)
		sql = f"""
			SELECT 
				name AS name,
				DATE(creation) AS creation,
				10 AS against_from, 
				debit AS `out`,
				credit AS `in`
			FROM
				`tabGL Entry`
			WHERE
				party = '{store.get("username")}'
			ORDER BY
				creation DESC
		"""

		transactions = frappe.db.sql(sql,as_dict=True)
		balance = get_balance(store.get("username"))

		frappe.local.response['http_status_code'] = 200
		frappe.local.response['transactions'] = transactions
		frappe.local.response['balance'] = float(balance or 0)
	except Exception as e:
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = e


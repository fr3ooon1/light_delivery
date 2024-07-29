import frappe
from frappe import _
import requests
from light_delivery.utils import validate_token
from frappe.utils import nowdate , get_first_day_of_week , get_first_day , getdate
from datetime import datetime
import json
 
@frappe.whitelist(allow_guest=True)
def new_order(full_name = None , phone_number = None, address = None, order_type = None, zone_address = None, invoice = None):
	doc = frappe.new_doc("Order")
	doc.full_name = full_name
	doc.phone_number = phone_number
	doc.address = address
	doc.order_type = order_type
	doc.zone_address = zone_address
	doc.invoice = invoice
	doc.insert()
	doc.save()


@frappe.whitelist(allow_guest=True)
def get_orders(user=None):
	# Validate the token
	# print("Hello")
	# validate_token()
	# url = "http://frappe.local:8000/api/method/frappe.auth.get_logged_user"
	# headers = {
	# 	'Authorization': "token <api_key>:<api_secret>"
	# }
	# response = requests.request("GET", url, headers=headers)
	
	if not user:
		user = "administrator"

	try:
		# Check if the user has the required role
		roles = frappe.get_roles(user)
		if 'Accounts User' in roles:
			# Get all orders with specific fields
			all_orders = frappe.get_list("Order", fields=['name', 'full_name', 'phone_number', 'address', 'invoice'])

			for order in all_orders:
				invoice = order.get("invoice")
				if invoice:
					file = frappe.get_doc("File", {"file_url": invoice})
					order['file'] = "http://84.247.182.89:81"+file.file_url

			# Construct response
			res = {}
			if all_orders:
				res = {
					'status_code': 200,
					'message': _('All Orders'),
					'data': all_orders
				}
			else:
				res = {
					'status_code': 204,
					'message': _('No Orders Found'),
					'data': all_orders
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
	
	
@frappe.whitelist(allow_guest=True)
def get_order_type(user = None):
	if not user:
		user = "administrator"
	try:
		roles = frappe.get_roles(user)
		if 'Accounts User' in roles:
			order_type = frappe.get_list("Order Type" , pluck ='name')
			res = {}
			if order_type:
				res = {
					'status_code' : 200 ,
					'message' : _('All data of Order Types') ,
					'data' : order_type
				}
				return res
			else:
				res = {
					'status_code' : 204 ,
					'message' : _('No Order Type Found'),
					'data' : order_type
				}
				return res
		
	except Exception as e:
		frappe.log_error(message=str(e), title=_('Error in get_order_type'))
		frappe.local.response['http_status_code'] = 500
		res = {
			"status_code": 500,
			"message": str(e)
		}
		return res

	
@frappe.whitelist(allow_guest=True)
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
	

import frappe
from frappe import _

@frappe.whitelist(allow_guest=True)
def get_zone_address(user=None):
	if not user:
		user = "administrator"
	try:
		roles = frappe.get_roles(user)
		if 'Accounts User' in roles:
			zone_addresses = frappe.get_list("Zone Address", pluck='name')
			if zone_addresses:
				return {
					'status_code': 200,
					'message': _('All data of Zone Address'),
					'data': zone_addresses
				}
			else:
				return {
					'status_code': 204,
					'message': _('No Zone Address found'),
					'data': []
				}
		else:
			return {
				'status_code': 403,
				'message': _('User does not have the required role'),
				'data': []
			}
	except Exception as e:
		frappe.log_error(message=str(e), title=_('Error in get_zone_address'))
		return {
			"status_code": 500,
			"message": str(e)
		}
	


@frappe.whitelist(allow_guest=True)
def get_order_history(status = None):
	# status = status.split(",")

	# return status
	try:
		orders = []

		if status == None or status == "All" or status == "ALL" or status == "all":
			orders = frappe.get_list("Order" ,  fields=['name', 'creation', 'status', 'total_order'])
		else:
			status = status.strip("[]").split(",")
			orders = frappe.get_list("Order" , filters = {'status':['in', status]} ,  fields=['name', 'creation', 'status' , 'total_order'])
		
		
		for order in orders:
			if isinstance(order.get('creation'), datetime):
				order['creation'] = order.get('creation').strftime('%Y-%m-%d %H:%M:%S')
			else:
				order['creation'] = datetime.strptime(order.get('creation'), '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
			
		today = nowdate()
		count_today = frappe.db.count('Order', filters={'creation': ['>=', today]})

		start_of_week = get_first_day_of_week(today)
		count_this_week = frappe.db.count('Order', filters={'creation': ['>=', start_of_week]})

		start_of_month = get_first_day(today)
		count_this_month = frappe.db.count('Order', filters={'creation': ['>=', start_of_month]})

		frappe.local.response['http_status_code'] = 200
		return {
			'status_code': 200,
			'message': _('Order History'),
			'data': {
				'orders': orders,
				'count_today':count_today ,
				'count_this_week' :count_this_week,
				'count_this_month': count_this_month
			}
		}
	except Exception as e:
		frappe.log_error(message=str(e), title=_('Error in get_order_history'))
		return {
			"status_code": 500,
			"message": str(e)
		}



@frappe.whitelist(allow_guest=True)
def get_order_state(user=None):
	if not user:
		user = "administrator"
	try:
		roles = frappe.get_roles(user)
		if 'Accounts User' in roles:
			
			"""
			Wait for Delivery
			Confirmed
			On The Way
			Delivered
			Refund
			"""

			wait_for_delivery = frappe.db.count('Order', {'status': 'Wait for Delivery'})
			confirmed = frappe.db.count('Order', {'status': 'Confirmed'})
			on_the_way = frappe.db.count('Order', {'status': 'On The Way'})
			delivered = frappe.db.count('Order', {'status': 'Delivered'})
			refund = frappe.db.count('Order', {'status': 'Refund'})
			all_orders = frappe.db.count('Order')

			order_states = {
					'wait_for_delivery': wait_for_delivery,
					'confirmed': confirmed,
					'on_the_way': on_the_way,
					'delivered': delivered,
					'refund': refund , 
					'all_orders': all_orders
				}
			
			"""
			Pending
			Avaliable
			Inorder
			Offline
			"""
			pending = frappe.db.count('Delivery', {'status': 'Pending'})
			avaliable = frappe.db.count('Delivery', {'status': 'Avaliable'})
			Inorder = frappe.db.count('Delivery', {'status': 'Inorder'})
			Offline = frappe.db.count('Delivery', {'status': 'Offline'})
			all_delivery = frappe.db.count('Delivery')

			delivery_states = {
					'pending':pending,
					'avaliable':avaliable,
					'Inorder':Inorder,
					'Offline':Offline,
					'all_delivery':all_delivery , 
				}
			
			
			"""
			Pending
			Active
			Inactive
			"""

			store_pending = frappe.db.count('Store', {'status': 'Pending'})
			store_active = frappe.db.count('Store', {'status': 'Active'})
			store_inactive = frappe.db.count('Store', {'status': 'Inactive'})
			all_stores = frappe.db.count('Store')

			stores_states = {
				'store_pending': store_pending,
				'store_active': store_active,
				'store_inactive': store_inactive,
				'all_stores': all_stores
			}


			frappe.local.response['http_status_code'] = 200
			return {
				'status_code': 200,
				'message': _('Count of order status'),
				'data': {
					'order_states': order_states,
					'delivery_states': delivery_states,
					# 'stores_states':stores_states
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
		frappe.log_error(message=str(e), title=_('Error in get_order_state'))
		return {
			"status_code": 500,
			"message": str(e)
		}
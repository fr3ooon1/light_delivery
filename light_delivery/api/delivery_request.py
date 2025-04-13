import frappe
from frappe import _
from light_delivery.api.apis import send_notification , search_delivary ,create_error_log
from frappe.utils import nowdate , get_first_day_of_week , get_first_day ,  get_datetime, now_datetime, time_diff_in_seconds

@frappe.whitelist(allow_guest=False)
def update_location(*args,**kwargs):
	try:
		if frappe.db.exists("Delivery",{"user":frappe.session.user}):
			doc = frappe.get_doc("Delivery",{"user":frappe.session.user})
			if doc.status not in ['Avaliable','Inorder']:
				return 
			doc.pointer_x = kwargs.get("pointer_x")
			doc.pointer_y = kwargs.get("pointer_y")
			doc.save(ignore_permissions=True)

			frappe.db.commit()
			frappe.local.response['http_status_code'] = 200
			frappe.local.response['message'] = _(f"""Update location""")

		else:
			frappe.local.response['http_status_code'] = 400
			frappe.local.response['message'] = _(f"""This Delivery not found""")

	except Exception as e:
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = _(e)


@frappe.whitelist()
def sending_request():
	requests = frappe.get_list("Request", {"status": "Waiting for Delivery"},order_by="creation asc")
	
	for request in requests:
		try:
			doc = frappe.get_doc("Request", request.get("name"))

			# if doc.status == "Offline":
			# 	return

			if doc.delivery :
				status = frappe.db.get_value("Delivery", doc.delivery, "status")
				if status in ["Inorder","Offline"]:
					if len(doc.deliveries) > 1:
						doc.deliveries = doc.deliveries[0:-1] 
						doc.save(ignore_permissions=True)
						frappe.db.commit()
					else:
						doc.deliveries = []
						doc.save(ignore_permissions=True)
						frappe.db.commit()
					continue
				# frappe.db.set_value("Delivery", doc.delivery, "status", "Avaliable")

			if doc.creation:
				now = now_datetime()
				creation = get_datetime(doc.creation)
				diff = time_diff_in_seconds(now, creation)/60
				if diff > 20:
					doc.status = "Cancel"
					doc.save(ignore_permissions=True)
					frappe.db.commit()
					continue

			order_type = frappe.get_value("Request Delivery",doc.name,"order_type")
			
			if not doc.deliveries:
				new_deliveries = search_delivary(cash=doc.cash, store=doc.store , order_type=order_type)

				if not new_deliveries:
					continue
				
				for delivery in new_deliveries:
					doc.append("deliveries", {
						"user": delivery.get("user"),
						"delivery": delivery.get("name"),
						"notification_key": delivery.get("notification_key"),
						"distance":delivery.get("distance")
					})
				
				doc.save(ignore_permissions=True)
				frappe.db.commit()

			if doc.deliveries:
				delivery = doc.deliveries[-1]
				delivery_obj = frappe.get_value("Delivery",delivery.get("delivery") , ["status","user"], as_dict=1)
				if delivery_obj.get("status") != "Avaliable":
					continue
				
				if delivery.get("notification_key"):
					res = send_notification(delivery.get("notification_key"), "new request")
					
					if res.status_code != 200:
						create_error_log("sending_request", res.text)

					doc.delivery = delivery.get("delivery")
					frappe.db.set_value("Delivery", delivery.get("delivery"), "status", "Hold")

				else:
					create_error_log("sending_request", "User not had a notification key")
				doc.deliveries = doc.deliveries[0:-1]
				doc.save(ignore_permissions=True)
				frappe.db.commit()
			
		except Exception as e:
			create_error_log("sending_request", frappe.get_traceback())
			frappe.db.commit()


			
@frappe.whitelist(allow_guest=False)
def delivery_accepted_request(*args , **kwargs):
	
	try:
		status = kwargs.get("status")
		request = kwargs.get("request")

		request_delivery = frappe.get_doc("Request Delivery",request )
		request = frappe.get_value("Request",request , "name")
		delivery = frappe.get_value("Delivery",{"user":frappe.session.user},["name","pointer_x","pointer_y","user"], as_dict=1)

		# doc = frappe.get_doc("Request" , request)

		if status == "Accepted":

			# doc.status = "Accepted"
			# delivery.status = "Inorder"

			frappe.db.set_value("Request", request, "status", "Accepted")
			frappe.db.set_value("Delivery", delivery.get("name"), "status", "Inorder")
			request_delivery.status = "Accepted"
			request_delivery.delivery = delivery.get("name")
			request_delivery.lat = delivery.get("pointer_x")
			request_delivery.lon = delivery.get("pointer_y")
			request_delivery.save(ignore_permissions=True)
			
			# frappe.db.set_value("Request Delivery", request_delivery, {
			# 	"status": "Accepted",
			# 	"delivery": delivery.get("name"),
			# 	"lat": delivery.get("pointer_x"),
			# 	"lon": delivery.get("pointer_y")
			# })
			store = request_delivery.store
			store_user = frappe.get_value("Store", store, "user")
			notification_key = frappe.get_value("User", store_user, "notification_key")
			if notification_key:
				res = send_notification(notification_key, "modification")
				if res.status_code != 200:
					frappe.log_error(
						message=f"Notification failed: {res.text}",
						title="Error in send_notification"
					)
			# delivery.save(ignore_permissions=True)
			# doc.save(ignore_permissions=True)

			# doc.append("log",{
			# 	"Delivery":delivery.get("name"),
			# 	"status":f"""{delivery.get("name")} Accept The Order""",
			# 	"time":now_datetime()
			# })
			# doc.save(ignore_permissions=True)

			frappe.db.commit()

			frappe.local.response['http_status_code'] = 200
			frappe.local.response['message'] = _(f"""the request accepted""")

		elif kwargs.get("status") != "Accepted":
			# delivery.status = "Avaliable"
			# delivery.save(ignore_permissions=True)
			# doc.delivery = None
			# doc.save(ignore_permissions=True)
			frappe.db.set_value("Delivery", delivery.get("name"), "status", "Avaliable")
			frappe.db.set_value("Request", request, "delivery", None)

			# doc.append("log",{
			# 	"Delivery":delivery.get("name"),
			# 	"status":f"""{delivery.get("name")} Reject The Order""",
			# 	"time":now_datetime()
			# })
			# doc.save(ignore_permissions=True)

			frappe.db.commit()

			frappe.local.response['http_status_code'] = 200
			frappe.local.response['message'] = _(f"""the request rejected""")

		log_request(request,delivery.get("name"),status)
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "delivery_accepted_request")
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = _(e)
		return {"status": "error", "message": str(e)}


# import ast

def log_request(request,delivery,status):
	doc = frappe.get_doc("Request Log", request)
	doc.append("log",{
		"delivery":delivery,
		"status":status,
		"time":now_datetime()
	})
	doc.save(ignore_permissions=True)
	frappe.db.commit()

@frappe.whitelist(allow_guest=False)
def get_delivery_request(*args, **kwargs):
	try:
		store = frappe.get_value("Store", {"user": frappe.session.user}, 'name')
		
		if not store:
			frappe.local.response['http_status_code'] = 400
			frappe.local.response['message'] = _( "No store found for the current user.")
			return {"status": "error", "message": "No store found for the current user."}
		
		orders = kwargs.get("orders")
		if not orders or not isinstance(orders, list):
			frappe.local.response['http_status_code'] = 400
			frappe.local.response['message'] = _( "No orders provided or invalid format." )
			return {"status": "error", "message": "No orders provided or invalid format."}

		
		request = frappe.new_doc("Request Delivery")
		request.store = store
		request.request_date = frappe.utils.nowdate()
		request.order_type = kwargs.get("order_type")

		for order_id in orders:
			request.append("order_request", {
				"order": order_id,
				"store": store
			})

		request.insert(ignore_permissions=True)
		frappe.db.commit()
		request.status = "Waiting for delivery"
		for order_id in orders:
			frappe.db.set_value("Order", order_id, "request", request.name)
		request.save(ignore_permissions=True)
		frappe.db.commit()

		frappe.local.response['http_status_code'] = 200
		frappe.local.response['message'] = _("Delivery request created successfully.")
		return {"status": "success", "message": "Delivery request created successfully.", "request_id": request.name}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "get_delivery_request")
		frappe.local.response['http_status_code'] = 400
		frappe.local.response['message'] = _(e)
		return {"status": "error", "message": str(e)}


def create_transaction(**kwargs):
	transaction = frappe.new_doc("Transactions")
	transaction.party = kwargs.get('party')
	transaction.party_type = kwargs.get('party_type')
	transaction.in_wallet = kwargs.get('in_wallet')
	transaction.out = kwargs.get('Out')
	# transaction.balance = kwargs.get('balance')
	transaction.aganist = kwargs.get('aganist')
	transaction.aganist_from = kwargs.get('aganist_from')
	transaction.voucher = kwargs.get('voucher')
	transaction.save(ignore_permissions=True)
	transaction.submit()
	frappe.db.commit()
	return transaction.name

@frappe.whitelist(allow_guest = 1)
def calculate_balane(party_type):
	balance = 0.0
	balance_data = frappe.db.sql(
		f'''
		SELECT
		 	 SUM(`in_wallet`) - SUM(`out`) AS total 
		FROM 
			`tabTransactions` 
		WHERE 
			party_type = '{party_type}'
		''',  
		as_dict=1
	)
	if balance_data :
		balance = balance_data[0]["total"]
	return balance

@frappe.whitelist()
def get_balance(party):
	balance = 0
	sql = f"""
			SELECT 
				SUM(jea.credit_in_account_currency) - SUM(jea.debit_in_account_currency) AS total
			FROM
				`tabJournal Entry Account` as jea
			WHERE
				jea.party = '{party}';

	"""
	sql = frappe.db.sql(sql,as_dict=1)
	if sql:
		balance = float(sql[0].get("total") or 0)
	return balance

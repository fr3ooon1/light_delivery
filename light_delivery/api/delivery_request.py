import frappe
from frappe import _
from light_delivery.api.apis import send_notification , search_delivary ,create_error_log

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
	requests = frappe.get_list("Request", {"status": "Waiting for Delivery"})
	
	for request in requests:
		try:
			doc = frappe.get_doc("Request", request.get("name"))

			if doc.delivery :
				frappe.db.set_value("Delivery", doc.delivery, "status", "Avaliable")
			
			if not doc.deliveries:
				new_deliveries = search_delivary(cash=doc.cash, store=doc.store)

				if not new_deliveries:
					return True
				
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
				delivery_obj = frappe.get_doc("Delivery",delivery.get("delivery"))
				if delivery_obj.status == "Hold":
					return "The Delivery has a request"
				
				if delivery.get("notification_key"):
					res = send_notification(delivery.get("notification_key"), "new request")
					
					if res.status_code != 200:
						create_error_log("sending_request", res.text)

					doc.delivery = delivery.get("delivery")
					delivery_obj.status = "Hold"
					delivery_obj.save(ignore_permissions=True)

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

	request = kwargs.get("request")
	doc = frappe.get_doc("Request",request)
	delivery = frappe.get_doc("Delivery",{"user":frappe.session.user})

	if kwargs.get("status") == "Accepted":
		doc.status = "Accepted"
		delivery.status = "Inorder"

		delivery.save(ignore_permissions=True)
		doc.save(ignore_permissions=True)
		frappe.db.commit()

		frappe.local.response['http_status_code'] = 200
		frappe.local.response['message'] = _(f"""the request accepted""")

	elif kwargs.get("status") != "Accepted":
		delivery.status = "Avaliable"
		delivery.save(ignore_permissions=True)
		frappe.db.commit()

		frappe.local.response['http_status_code'] = 200
		frappe.local.response['message'] = _(f"""the request rejected""")



import ast


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


# @frappe.whitelist(allow_guest = 0 )
# def get_delivery_request():
# 	store = frappe.db.sql(f"select name from `tabStore` where user = '{frappe.session.user}' " , as_dict = 1)
# 	sql = f'''
# 			select 
# 				r.name , r.delivery ,
# 				GROUP_CONCAT(o.order ORDER BY o.order SEPARATOR ',') AS orders
# 			from 
# 				`tabRequest Delivery` r
# 			inner join
# 				`tabOrder Request` o
# 				on 
# 				r.name = o.parent
# 			where 
# 				r.store = '{store[0]["name"]}'
# 			group by 
# 				r.name , r.delivery
# 			'''
# 	requests = frappe.db.sql(sql , as_dict = 1)
# 	if requests :
# 		for request in requests :
# 			request['orders'] = request['orders'].split(',')
# 			delivery_pointers = frappe.db.sql(f'''select pointer_x , pointer_y from `tabDelivery` where name = '{request["delivery"]}' ''', as_dict = 1)
# 			request["pointer_x"] = delivery_pointers[0]["pointer_x"]
# 			request["pointer_y"] = delivery_pointers[0]["pointer_y"]
		
# 	return requests

# @frappe.whitelist(allow_guest = 0 )
# def delivery_cancel_request(request_id , status):
# 	user = frappe.db.sql(f"select name from `tabDelivery` where user = '{frappe.session.user}' " , as_dict = 1) 
# 	if not user :
# 		return "You don't have permision"
# 	request = frappe.db.sql( f'''select delivery , store from `tabRequest Delivery` where name = '{request_id}'  ''' ,as_dict =1 )
# 	minimum_rate = frappe.db.sql( 
# 		f'''select  
# 				c.minimum_rate , d.cash
# 			from 
# 				`tabDelivery Category` c
# 			inner join 
# 				`tabDelivery` d 
# 			on 
# 				d.delivery_category = c.name
# 			where 
# 				d.name = '{request[0]["delivery"]}'  '''   , as_dict = 1)
# 	fees = (minimum_rate[0]["minimum_rate"] * 50) / 100

# 	balance = balance - fees
# 	frappe.db.sql(f""" UPDATE `tabOrder Log` 
# 					SET status = "Delivery Cancel" 
# 			   WHERE parent = '{request_id}' """)
# 	frappe.db.commit()
# 	create_transaction(party = "Delivery" , party_type = request[0]["delivery"],
# 						In= 0.0 , Out = float(fees), balance = balance , aganist = "Store", aganist_from = request[0]["store"] ,  voucher = "Pay Planty")




# @frappe.whitelist(allow_guest = 0 )
# def delivery_cancel_request(request_id , status):
# 	user = frappe.db.sql(f"select name from `tabDelivery` where user = '{frappe.session.user}' " , as_dict = 1) 
# 	if not user :
# 		return "You don't have permision"
# 	frappe.db.sql(
# 			f""" UPDATE 
# 				`tabRequest Delivery` 
# 			SET 
# 				status = "Delivery Cancel" 
# 			WHERE 
# 				name = '{request_id}' """)
# 	frappe.db.commit()
	
	# request = frappe.db.sql( f'''select delivery , store from `tabRequest Delivery` where name = '{request_id}'  ''' ,as_dict =1 )

	# frappe.db.sql(f""" UPDATE `tabOrder Log` 
	# 				SET status = "Delivery Cancel" 
	# 		WHERE parent = '{request_id}' """)
	# frappe.db.commit()
	# create_transaction(party = "Delivery" , party_type = request[0]["delivery"],
	# 					In= 0.0 , Out = float(fees), balance = balance , aganist = "Store", aganist_from = request[0]["store"] ,  voucher = "Pay Planty")	

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

# @frappe.whitelist(allow_guest = 0 )
# def store_cancel_request(request_id):
# 	user = frappe.db.sql(f"select name from `tabStore` where user = '{frappe.session.user}' " , as_dict = 1)
# 	if not user :
# 		return "You don't have permision"
# 	request = frappe.db.sql( f'''select delivery , store from `tabRequest Delivery` where name = '{request_id}'  ''' ,as_dict =1 )
# 	return request
	# minimum_rate = frappe.db.sql( 
	# 	f'''select  
	# 			c.minimum_rate , d.cash
	# 		from 
	# 			`tabDelivery Category` c
	# 		inner join 
	# 			`tabDelivery` d 
	# 		on 
	# 			d.delivery_category = c.name
	# 		where 
	# 			d.name = '{request[0]["delivery"]}'  '''   , as_dict = 1)
	# fees = (minimum_rate[0]["minimum_rate"] * 50) / 100
	# balance = 0.0
	# balance_data = frappe.db.sql(f'''select balance 
	# 						from 
	# 						  	`tabTransactions` 
	# 						where 
	# 						  	party_type = '{request[0]["delivery"]}' and aganist_from = '{request[0]["store"]}'
	# 						ORDER BY creation DESC 
	# 						limit 1''' , as_dict = 1) 
	# if balance_data :
	# 	balance = balance_data[0]["balance"]
	# balance = balance - fees
	# frappe.db.sql(f""" UPDATE `tabOrder Log` 
	# 				SET status = "Delivery Cancel" 
	# 		   WHERE parent = '{request_id}' """)
	# frappe.db.commit()
	# create_transaction(party = "Delivery" , party_type = request[0]["delivery"],
	# 					In= 0.0 , Out = float(fees), balance = balance , aganist = "Store", aganist_from = request[0]["store"] ,  voucher = "Pay Planty")	
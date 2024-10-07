import frappe
from frappe import _
from light_delivery.api.apis import send_notification

@frappe.whitelist(allow_guest=False)
def update_location(*args,**kwargs):
	try:
		if frappe.db.exists("Delivery",{"user":frappe.session.user}):
			doc = frappe.get_doc("Delivery",{"user":frappe.session.user})
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
	requests = frappe.get_list("Request",{"status":"Waiting for Delivery"})
	try:
		if requests:
			for request in requests:
				doc = frappe.get_doc("Request",request.get("name"))
				deliveries = doc.get("deliveries")[0]
				res = send_notification(deliveries.get("notification_key")) if deliveries.get("notification_key") else None
				if res.status_code == 200:
					doc.append("deliveries",{
						"user":deliveries.get("user"),
						"delivery":deliveries.get("delivery"),
						"notification_key":deliveries.get("notification_key")
					})
					doc.delivery = deliveries.get("delivery")
					doc.remove(doc.deliveries[0])

					doc.save(ignore_permissions=True)
					frappe.db.commit()
					
				else:
					error = frappe.new_doc("Error Log")
					error.method = "sending_request"
					error.error = res.text
					error.save(ignore_permissions=True)
					frappe.db.commit()
				return res

	except Exception as e:
		error = frappe.new_doc("Error Log")
		error.method = "sending_request"
		error.error = e
		error.save(ignore_permissions=True)
		frappe.db.commit()


			
@frappe.whitelist(allow_guest=False)
def delivery_accepted_request(*args , **kwargs):
	delivery = frappe.get_value("Delivery",{"user":frappe.session.user},'name')
	request = kwargs.get("request")
	doc = frappe.get_doc("Request",request)
	if kwargs.get("status") == "Accept":
		doc.status = "Accepted"
		doc.delivery = delivery
		doc.save(ignore_permissions=True)
		frappe.db.commit()
	elif kwargs.get("status") == "Reject":
		pass


@frappe.whitelist(allow_guest = 0 )
def get_delivery_request():
	store = frappe.db.sql(f"select name from `tabStore` where user = '{frappe.session.user}' " , as_dict = 1)
	sql = f'''
			select 
				r.name , r.delivery ,
				GROUP_CONCAT(o.order ORDER BY o.order SEPARATOR ',') AS orders
			from 
				`tabRequest Delivery` r
			inner join
				`tabOrder Request` o
				on 
				r.name = o.parent
			where 
				r.store = '{store[0]["name"]}'
			group by 
				r.name , r.delivery
			'''
	requests = frappe.db.sql(sql , as_dict = 1)
	if requests :
		for request in requests :
			request['orders'] = request['orders'].split(',')
			delivery_pointers = frappe.db.sql(f'''select pointer_x , pointer_y from `tabDelivery` where name = '{request["delivery"]}' ''', as_dict = 1)
			request["pointer_x"] = delivery_pointers[0]["pointer_x"]
			request["pointer_y"] = delivery_pointers[0]["pointer_y"]
		
	return requests

@frappe.whitelist(allow_guest = 0 )
def delivery_cancel_request(request_id , status):
	user = frappe.db.sql(f"select name from `tabDelivery` where user = '{frappe.session.user}' " , as_dict = 1) 
	if not user :
		return "You don't have permision"
	request = frappe.db.sql( f'''select delivery , store from `tabRequest Delivery` where name = '{request_id}'  ''' ,as_dict =1 )
	minimum_rate = frappe.db.sql( 
		f'''select  
				c.minimum_rate , d.cash
			from 
				`tabDelivery Category` c
			inner join 
				`tabDelivery` d 
			on 
				d.delivery_category = c.name
			where 
				d.name = '{request[0]["delivery"]}'  '''   , as_dict = 1)
	fees = (minimum_rate[0]["minimum_rate"] * 50) / 100

	balance = balance - fees
	frappe.db.sql(f""" UPDATE `tabOrder Log` 
					SET status = "Delivery Cancel" 
			   WHERE parent = '{request_id}' """)
	frappe.db.commit()
	create_transaction(party = "Delivery" , party_type = request[0]["delivery"],
						In= 0.0 , Out = float(fees), balance = balance , aganist = "Store", aganist_from = request[0]["store"] ,  voucher = "Pay Planty")




@frappe.whitelist(allow_guest = 0 )
def delivery_cancel_request(request_id , status):
	user = frappe.db.sql(f"select name from `tabDelivery` where user = '{frappe.session.user}' " , as_dict = 1) 
	if not user :
		return "You don't have permision"
	frappe.db.sql(
			f""" UPDATE 
				`tabRequest Delivery` 
			SET 
				status = "Delivery Cancel" 
			WHERE 
				name = '{request_id}' """)
	frappe.db.commit()
	
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

@frappe.whitelist(allow_guest = 0 )
def store_cancel_request(request_id):
	user = frappe.db.sql(f"select name from `tabStore` where user = '{frappe.session.user}' " , as_dict = 1)
	if not user :
		return "You don't have permision"
	request = frappe.db.sql( f'''select delivery , store from `tabRequest Delivery` where name = '{request_id}'  ''' ,as_dict =1 )
	return request
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
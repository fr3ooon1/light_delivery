# Copyright (c) 2024, Muhammad Essam and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class RequestDelivery(Document):
	def validate(self):
		if self.status == "Delivery Cancel":
			pass
		if self.status == "Store Cancel":
			pass
		
# def delivery_cancel_request(request_id):
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
# 	balance = 0.0
# 	balance_data = frappe.db.sql(f'''select balance 
# 							from 
# 							  	`tabTransactions` 
# 							where 
# 							  	party_type = '{request[0]["delivery"]}' and aganist_from = '{request[0]["store"]}'
# 							ORDER BY creation DESC 
# 							limit 1''' , as_dict = 1) 
# 	if balance_data :
# 		balance = balance_data[0]["balance"]
# 	balance = balance - fees
# 	frappe.db.sql(f""" UPDATE `tabOrder Log` 
# 					SET status = "Delivery Cancel" 
# 			   WHERE parent = '{request_id}' """)
# 	frappe.db.commit()
# 	create_transaction(party = "Delivery" , party_type = request[0]["delivery"],
# 						In= 0.0 , Out = float(fees), balance = balance , aganist = "Store", aganist_from = request[0]["store"] ,  voucher = "Pay Planty")
# Copyright (c) 2024, Muhammad Essam and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime
from light_delivery.api.delivery_request import create_transaction , calculate_balane
from light_delivery.api.apis import search_delivary



class RequestDelivery(Document):
	def before_naming(self):
		self.follow_request_status()
	def validate(self):
		if self.status not in ['Pending' ,'Accepted','Collect Money']:
			self.follow_request_status()
			self.request_accepted()
		if self.status == "Accepted":
			pass
		if self.status in ['Arrived' , 'Picked' , 'Delivery Cancel' , 'Store Cancel' , 'Cancel', 'Accepted']:
			self.change_status_for_orders()

		if self.status == "Waiting for delivery":
			self.follow_request_status()
			self.create_request()
		
		if self.status in ["Delivered" , 'Delivery Cancel' , 'Store Cancel' , 'Cancel' ]:
			self.close_request()
			
		if self.status == "Collect Money":
			self.pay_to_store()


	def pay_to_store(self):
		balance =  float(calculate_balane(self.delivery) or 0)

		temp = balance - self.total

		doc = frappe.new_doc("Transactions")
		doc.party = "Delivery"
		doc.party_type = self.delivery
		doc.out = abs(temp)
		doc.aganist = "Store"
		doc.aganist_from = self.store
		doc.save(ignore_permissions=True)
		doc.submit()

		store = frappe.new_doc("Transactions")
		store.party = "Store"
		store.party_type = self.store
		store.in_wallet = abs(temp)
		store.aganist = "Delivery"
		store.aganist_from = self.delivery
		store.save(ignore_permissions=True)
		store.submit()

		frappe.db.commit()

	def close_request(self):
		if self.delivery:
			doc = frappe.get_doc("Delivery",self.delivery)
			doc.status = "Offline"
			doc.save(ignore_permissions=True)
			frappe.db.commit()
			
		

	def create_request(self):
		doc = frappe.new_doc("Request")
		doc.request_delivery = self.name
		doc.status = "Waiting for Delivery"
		doc.store = self.store
		doc.cash = self.total
		doc.number_of_order = self.number_of_order
		deliveries = search_delivary(self.total , self.store)

		if deliveries:
			for i in deliveries:
				doc.append("deliveries",{
					"user" :i.get('user'), 
					"delivery":i.get('name'),
					"notification_key":frappe.get_value("User",i.get('user'),"notification_key")
				})

		doc.save(ignore_permissions=True)
		frappe.db.commit()

	def request_accepted(self):
		order_request = self.order_request
		self.number_of_order = len(order_request)
		store = frappe.get_doc("Store",self.store)
		store_discount = store.get('store_discount')

		total_request_amount = 0

		for i in range(len(order_request)):
			order = frappe.get_doc("Order" , self.get('order_request')[i].get("order"))
			order.discount = store_discount[i].get("discount") if store_discount else 0

			# self.order_request[i] = self.delivery

			order.delivery = order_request[i].get("delivery")
			order.store = order_request[i].get("store")
			order.status = self.status

			total_request_amount += float(order.get("total_order") or 0)

			order.save(ignore_permissions=True)
		self.total = total_request_amount


	def change_status_for_orders(self):
		order_request = self.get('order_request')
		for order in order_request:
			doc = frappe.get_doc("Order" , order.order)
			if doc.status not in ['Cancel' , 'Delivery Cancel','Store Cancel']:
				doc.status = self.status
				doc.save(ignore_permissions=True)


	def delivery_cancel(self):
		self.follow_request_status()
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
				d.name = '{self.delivery}'  '''   , as_dict = 1)
		fees = (minimum_rate[0]["minimum_rate"] * 50) / 100
		create_transaction(party = "Delivery" , party_type = self.delivery,
						in_wallet= 0.0 , Out = float(fees) , aganist = "Store", aganist_from = self.store ,  voucher = "Pay Planty")	
	
	def follow_request_status(self):
		self.append("request_log",{
			"status":self.status,
			"time": now_datetime(),
		})
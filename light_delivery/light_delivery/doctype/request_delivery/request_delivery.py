# Copyright (c) 2024, Muhammad Essam and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime
from light_delivery.api.delivery_request import create_transaction , get_balance
from light_delivery.api.apis import search_delivary , make_journal_entry , Deductions



class RequestDelivery(Document):

	Deductions = frappe.get_doc("Deductions")


	def before_naming(self):
		self.calculate_orders()
		self.follow_request_status()


	def validate(self):
		self.rate_store()
		if self.status not in ['Pending' ,'Accepted','Collect Money']:
			self.follow_request_status()
			
		if self.status == "Accepted":
			self.request_accepted()
			
		if self.status in ['Arrived' , 'Picked' , 'Cancel' , 'Delivery Cancel','Store Cancel','Waiting for delivery','On The Way']:
			self.change_status_for_orders()

		if self.status == "Waiting for delivery":
			self.follow_request_status()
			self.create_request()
		
		if self.status in ["Delivered" , 'Delivery Cancel' , 'Store Cancel' , 'Cancel' ]:
			self.close_request()
			
		if self.status == "Collect Money" and self.payed_to_store == 0:
			self.pay_to_store()


	# 	if self.status == "Picked":
	# 		self.start_point()


	# def start_point(self):
	# 	self.lat = frappe.get_value("Delivery",self.delivery,"pointer_x")
	# 	self.lon = frappe.get_value("Delivery",self.delivery,"pointer_y")




	def calculate_orders(self):
		total_request_amount = 0
		order_request = self.order_request
		self.number_of_order = len(order_request)
		for i in range(len(order_request)):
			total_request_amount += frappe.get_value("Order" , self.get('order_request')[i].get("order") , "total_order")
		self.total = total_request_amount


	def rate_store(self):
		if self.delivery:
			if self.valuation and frappe.db.exists("Store",self.store):
				del_obj = frappe.get_doc("Store" , self.store)
				del_obj.num_of_rates = float(del_obj.num_of_rates or 0) + 1
				del_obj.total_rates = float(del_obj.total_rates or 0) + float(self.valuation or 0)
				del_obj.save(ignore_permissions=True)
				frappe.db.commit()


	def pay_to_store(self):
		delivery_name = frappe.get_value("Delivery",self.delivery,'delivery_name')
		balance =  float(get_balance(delivery_name) or 0)

		Deductions = frappe.get_doc("Deductions")

		temp = 0
		if balance < self.total:
			temp = balance
		if balance >= self.total:
			temp = self.total

		if temp > 0 :
			print(temp)

			transaction = {
					"account_credit": Deductions.store_account,
					"party_type_credit": "Customer",
					"party_credit": frappe.get_value("Store",self.store,'username'),
					"amount_credit":temp,

					"account_debit": Deductions.delivery_account,
					"party_type_debit": "Supplier",
					"party_debit": frappe.get_value("Delivery",self.delivery,'delivery_name'),
					"amount_debit": temp,

					"order":f"""{self.name}"""
					}
			make_journal_entry(transaction)
			self.payed_to_store = 1
			

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
		self.finish_request = 1
		if self.delivery:
			doc = frappe.get_doc("Delivery",self.delivery)
			doc.status = "Offline"
			doc.cash = 0
			doc.save(ignore_permissions=True)
			frappe.db.commit()
			
		

	def create_request(self):
		if frappe.db.exists("Request",self.name):
			return 
		doc = frappe.new_doc("Request")
		doc.request_delivery = self.name
		doc.status = "Waiting for Delivery"
		doc.store = self.store

		total_request_amount = 0

		order_request = self.order_request
		self.number_of_order = len(order_request)
		for i in range(len(order_request)):
			total_request_amount += frappe.get_value("Order" , self.get('order_request')[i].get("order") , "total_order")
		doc.cash = total_request_amount
		doc.number_of_order = len(order_request)
		deliveries = search_delivary(total_request_amount , self.store)

		if deliveries:
			for i in deliveries:
				doc.append("deliveries",{
					"user" :i.get('user'), 
					"delivery":i.get('name'),
					"notification_key":frappe.get_value("User",i.get('user'),"notification_key"),
					"distance":i.get("distance")
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

			order.delivery = self.delivery
			order.store = self.store
			order.status = self.status

			total_request_amount += float(order.get("total_order") or 0)

			order.save(ignore_permissions=True)
		self.total = total_request_amount


	def change_status_for_orders(self):
		order_request = self.get('order_request')
		for order in order_request:
			doc = frappe.get_doc("Order" , order.order)
			if doc.status not in ['Cancel' , 'Delivered']:
				if self.status not in ["Collect Money"]:
					if self.status in ['Delivery Cancel','Cancel','Store Cancel']:
						return
						doc.status = "Cancel"
					else:
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
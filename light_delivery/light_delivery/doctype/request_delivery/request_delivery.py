# Copyright (c) 2024, Muhammad Essam and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime
from light_delivery.api.delivery_request import create_transaction


class RequestDelivery(Document):
	def validate(self):
		# if self.status == "Delivery Cancel":
		# 	# self.delivery_cancel()
		# if self.status == "Store Cancel":
		# 	pass
		if self.status == "Accepted":
			self.request_accepted()
		if self.status in ['Arrived' , 'Picked' , 'Delivery Cancel' , 'Store Cancel' , 'Cancel']:
			self.change_status_for_orders()
			
	
	def request_accepted(self):
		order_request = self.order_request
		self.number_of_order = len(order_request)
		store = frappe.get_doc("Store",self.store)
		store_discount = store.get('store_discount')
		if not store_discount:
			return False
		for i in range(len(order_request)):
			order = frappe.get_doc("Order" , self.get('order_request')[i].get("order"))
			order.discount = store_discount[i].get("discount")

			order.delivery = order_request[i].get("delivery")
			order.store = order_request[i].get("store")
			order.status = self.status

			order.save(ignore_permissions=True)


	def change_status_for_orders(self):
		order_request = self.get('order_request')
		for order in order_request:
			doc = frappe.get_doc("Order" , order.order)
			doc.status = self.status
			doc.save(ignore_permissions=True)


	def delivery_cancel(self):
		self.follow_request_status(self.status)
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
	
	def follow_request_status(self , status ):
		self.append("order_log",{
			"status":status,
			"time": now_datetime(),
		})
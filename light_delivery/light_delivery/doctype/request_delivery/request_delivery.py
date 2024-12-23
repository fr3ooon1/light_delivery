# Copyright (c) 2024, Muhammad Essam and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime
from light_delivery.api.delivery_request import create_transaction , get_balance
from light_delivery.api.apis import search_delivary , make_journal_entry 
import datetime
from frappe.utils import now_datetime , get_datetime , time_diff_in_seconds



class RequestDelivery(Document):

	def before_naming(self):
		self.calculate_orders()
		self.follow_request_status()


	def validate(self):
		self.calculate_orders()
		self.get_deduction()
		self.rate_store()
		if self.status not in ['Pending' ,'Accepted','Collect Money']:
			self.follow_request_status()
			
		if self.status == "Accepted":
			self.request_accepted()
			
		if self.status in ['Arrived' , 'Picked' , 'Cancel' , 'Delivery Cancel','Store Cancel','Waiting for delivery','On The Way']:
			self.change_status_for_orders()

		if self.status == "Waiting for delivery":
			self.create_request()
		
		if self.status in ["Delivered" , 'Delivery Cancel' , 'Store Cancel' , 'Cancel' ]:
			self.close_request()
			
		if self.status == "Collect Money" and self.payed_to_store == 0:
			self.pay_to_store()

		

	
	def get_deduction(self):
	
		if self.status == "Arrived":
			self.late_after_accept()

		if self.status == "Cancel":
			self.cancele_from_store_after_picked_up()
			self.cancele_from_store_after_delivery_arrived()
		
		if self.status == "Picked":
			self.pick_up_deduction()


	def late_after_accept(self):

		Deductions = frappe.get_doc("Deductions")
		request_log = self.get("request_log")
		accepted_row = next((row for row in request_log if row.get('status') == "Accepted"), None)
		if accepted_row:
			time_difference = time_diff_in_seconds(now_datetime(), get_datetime(accepted_row.get("time")))
			if float(time_difference or 0) / 60 > float(Deductions.late_after_accept or 0):
				self.status = "Delivery Cancel"

				delivery_category = frappe.get_value("Delivery", self.delivery , "delivery_category")
				minimum_rate = frappe.get_value("Delivery Category" , delivery_category , "minimum_rate")

				delivery = {
					"account_credit": Deductions.expens_account,
					"amount_credit": minimum_rate / 2,

					"account_debit": Deductions.delivery_account,
					"party_type_debit": "Supplier",
					"party_debit": frappe.get_value("Delivery",self.delivery,'delivery_name'),
					"amount_debit":minimum_rate / 2,	

					"order":self.name
					}
				
				if minimum_rate > 0 :
					make_journal_entry(delivery)

				frappe.db.set_value("Request",self.name,"status","Waiting for delivery")




	def cancele_from_store_after_picked_up(self):
		if self.finish_request == 0:
			if self.status == "Store Cancel":
				request_log = self.get("request_log")
				if request_log:
					last_log = next((row for row in request_log if row.get('status') == "Picked"), None)
					if last_log:
						order_request = self.get('order_request')
						if order_request:
							for order in order_request:
								doc = frappe.get_doc("Order" , order.order)
								finish_order_with_rate(doc=doc , rate=1.5)
							self.finish_request = 1


	def cancele_from_store_after_delivery_arrived(self):
		if self.finish_request == 0:
			if self.status == "Store Cancel":
				request_log = self.get("request_log")
				if request_log:
					last_log = next((row for row in request_log if row.get('status') == "Arrived"), None)
					if last_log:
						order_request = self.get('order_request')
						if order_request:
							for order in order_request:
								doc = frappe.get_doc("Order" , order.order)
								finish_order_with_rate(doc=doc , rate=1)
							self.finish_request = 1
	

	def pick_up_deduction(self):
		Deductions = frappe.get_doc("Deductions")
		pick_up_deduction = Deductions.get("pick_up_deduction")
		request_log = self.get("request_log")
		rate = 0
		if not request_log or not pick_up_deduction:
			return
		time_difference = float(time_diff_in_seconds(now_datetime(), get_datetime(request_log[-1].get("time")))) / 60
		row = next(
			(i for i in pick_up_deduction if i.get("from") < time_difference <= i.get("to")),
			None
		)

		try:
			rate = row.get("rate")
			if rate >= 100:
				self.status = "Store Cancel"
			
			order_request = self.get('order_request')
			if order_request:
				for order in order_request:
					doc = frappe.get_doc("Order" , order.order)
					finish_order_with_rate(doc=doc , rate=1)
				self.finish_request = 1
		except Exception as e:
			frappe.log_error(f"Error in {self.name}: {str(e)}", "Pick Up Deduction Error")


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
			frappe.log_error(f"Error in {self.name}: Request Already Exists", "Request Already Exists")
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

		frappe.db.commit()


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




def finish_order_with_rate(doc , rate ):

	total = 0

	Deductions = frappe.get_doc("Deductions")

	if doc.delivery:
		if frappe.db.exists("Delivery Category" , frappe.get_value("Delivery" , doc.delivery , 'delivery_category')):
			delivery_category = frappe.get_doc(
				"Delivery Category" , 
				frappe.get_value("Delivery" , doc.delivery , 'delivery_category')
			)

			total = float(delivery_category.minimum_rate or 0) * rate

			total =(total - (total / 100 * doc.discount))
			doc.delivery_fees = total 
			
			doc.net_delivery_fees = total

			

			doc = frappe.new_doc("Transactions")
			doc.party = "Delivery"
			doc.party_type = doc.delivery
			doc.in_wallet = total
			doc.aganist = "Store"
			doc.aganist_from = doc.store
			doc.order = doc.name
			doc.save(ignore_permissions=True)
			doc.submit()
	
	if doc.store:
		store = frappe.get_doc("Store" , doc.store)

		total = float(store.minimum_price or 0) * rate
		
		tax = frappe.db.get_single_value('Deductions', 'rate_of_tax')

		tax_rate = (total * tax / 100)

		total_with_tax = total + tax_rate
		discount = total_with_tax - (total_with_tax / 100 * doc.discount)

		doc.net_store_fees = total
		doc.tax = tax_rate
		doc.store_fees = discount

		doc = frappe.new_doc("Transactions")
		doc.party = "Store"
		doc.party_type = doc.store
		doc.out = total
		doc.aganist = "Delivery"
		doc.aganist_from = doc.delivery
		doc.order = doc.name
		doc.save(ignore_permissions=True)
		doc.submit()
	frappe.db.commit()


	store = {
		"account_credit": Deductions.light_account,
		"amount_credit":float(doc.store_fees or 0) - float(doc.tax or 0),

		"account_debit": Deductions.store_account,
		"party_type_debit": "Customer",
		"party_debit": frappe.get_value("Store",doc.store,'username'),
		"amount_debit": float(doc.store_fees or 0) - float(doc.tax or 0),

		"order":doc.name
		}
	if doc.net_store_fees > 0:
		make_journal_entry(store)
	
	tax = {
		"account_credit": Deductions.tax_account,
		"amount_credit": doc.tax,

		"account_debit": Deductions.store_account,
		"party_type_debit": "Customer",
		"party_debit": frappe.get_value("Store",doc.store,'username'),
		"amount_debit":doc.tax,

		"order":doc.name
		}
	if doc.tax > 0 :
		make_journal_entry(tax)


	delivery = {
		"account_debit": Deductions.expens_account,
		"amount_debit": doc.delivery_fees,

		"account_credit": Deductions.delivery_account,
		"party_type_credit": "Supplier",
		"party_credit": frappe.get_value("Delivery",doc.delivery,'delivery_name'),
		"amount_credit":doc.delivery_fees ,	

		"order":doc.name
		}
	
	if doc.delivery_fees > 0 :
		make_journal_entry(delivery)

	prof_delivery = {
		"account_debit": Deductions.delivery_account,
		"party_type_debit": "Supplier",
		"party_debit": frappe.get_value("Delivery",doc.delivery,'delivery_name'),
		"amount_debit":doc.delivery_fees,

		"account_credit": Deductions.balance,
		"party_type_credit": "Supplier",
		"party_credit": frappe.get_value("Delivery",doc.delivery,'delivery_name'),
		"amount_credit":doc.delivery_fees,	

		"order":doc.name
		}
	if doc.delivery_fees > 0:
		make_journal_entry(prof_delivery)
	
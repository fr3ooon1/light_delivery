# Copyright (c) 2024, Muhammad Essam and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now , get_datetime , now_datetime , time_diff_in_seconds
from light_delivery.api.delivery_request import create_transaction


class RequestDelivery(Document):
	def validate(self):
		self.track_order_number()
		if self.status == "Accepted":
			self.follow_request_status(self.status)
		if self.status == "Arrived":
			self.delivery_arrived()
		if self.status == "Delivery Cancel":
			self.delivery_cancel()
		if self.status == "Store Cancel":
			self.store_cancel()

	def track_order_number(self):
		if len(self.order_request) == 2 :
			for item in self.order_request :
				store_discount = frappe.db.sql (f''' select d.order , d.discount from `tabStore Discount` d inner join `tabStore` s where s.name='{self.store}' ''')
				frappe.throw(str(store_discount))
				if item.idx == 2:
					frappe.db.set_value('Order',item.order,'discount',)
					# minimum_rate = frappe.db.sql( 
					# f'''select  
					# 		c.minimum_rate , d.cash
					# 	from 
					# 		`tabDelivery Category` c
					# 	inner join 
					# 		`tabDelivery` d 
					# 	on 
					# 		d.delivery_category = c.name
					# 	where 
					# 		d.name = '{self.delivery}'  '''   , as_dict = 1)
					
		if len(self.order_request) == 3 :
			pass
		if len(self.order_request) == 4 :
			pass
			

	def delivery_arrived(self):
		self.follow_request_status(self.status)
		sql = f'''select o.time from `tabOrder Log` o inner join `tabRequest Delivery` r on o.parent = r.name where o.status="Accepted"  '''
		accept = frappe.db.sql(sql , as_dict = 1)
		if accept :
			accept =get_datetime (accept[0]["time"])
		sql1 = f'''select o.time from `tabOrder Log` o inner join `tabRequest Delivery` r on o.parent = r.name where o.status="Arrived"  '''
		arrived = frappe.db.sql(sql1 , as_dict =1 )
		if arrived :
			arrived = get_datetime(arrived[0]["time"])
		if accept and arrived :
			timetime_diff_in_min=time_diff_in_seconds(arrived , accept)/ 60
			late_after_accept = frappe.db.get_single_value("Deductions", "late_after_accept")
			if timetime_diff_in_min > late_after_accept :
				self.status = "Cancel"
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

	def store_cancel(self):
		self.follow_request_status(self.status)
		minimum_rate = frappe.db.sql( 
		f'''select  
				minimum_price
			from 
				`tabStore`
			where 
				name = '{self.store}'  '''   , as_dict = 1)
		fees = (minimum_rate[0]["minimum_price"] * 50) / 100
		create_transaction(party = "Store" , party_type = self.store,
						in_wallet= 0.0 , Out = fees , aganist = "Delivery", aganist_from = self.delivery ,  voucher = "Pay Planty")		
	
	def follow_request_status(self , status ):
		self.append("request_log",{
			"status":status,
			"time": now(),
		})
	# frappe.db.commit()

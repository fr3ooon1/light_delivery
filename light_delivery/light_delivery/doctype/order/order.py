# Copyright (c) 2024, Muhammad Essam and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
import json
from frappe.utils import now_datetime , format_duration, get_datetime , time_diff_in_seconds
from light_delivery.api.apis import osm_v2 ,osm_v1, make_journal_entry , Deductions
from datetime import datetime


class Order(Document):
	def before_naming(self):
		self.begain_order()


	def validate(self):
		self.get_deduction()
		self.order_status()
		self.get_previous_order_amount()
		self.rate_delivery()
		self.change_request_status()
		self.calculate_distance_duration()	
		self.cancellation_from_delivery()


	def cancellation_from_delivery(self):
		if self.status == "Cancel" and self.cancel_from == "Delivery":
			doc = frappe.new_doc("Order")
			doc.order_type = self.order_type
			doc.full_name = self.full_name
			doc.phone_number = self.phone_number
			doc.address = self.address
			doc.zone_address = self.zone_address
			doc.invoice = self.invoice
			doc.total_order = self.total_order
			doc.save(ignore_permissions=True)
			frappe.db.commit()


	def calculate_distance_duration(self):
		if self.status == "On The Way":
			self.start_lat = float(frappe.db.get_value("Delivery",self.delivery,"pointer_x"))
			self.start_lon = float(frappe.db.get_value("Delivery",self.delivery,"pointer_y"))

		if self.status in ["Arrived For Destination"]:
			self.end_lat = float(frappe.db.get_value("Delivery",self.delivery,"pointer_x"))
			self.end_lon = float(frappe.db.get_value("Delivery",self.delivery,"pointer_y"))

			start_coordi = float(self.start_lat) , float(self.start_lon)
			end_coordi = float(frappe.db.get_value("Delivery",self.delivery,"pointer_x")) , float(frappe.db.get_value("Delivery",self.delivery,"pointer_y"))
			
			# res = osm_v2(start_coordi,end_coordi)
			res = osm_v2(str(f"""{self.start_lat},{self.start_lon}"""),str(f"""{frappe.db.get_value("Delivery",self.delivery,"pointer_x")},{frappe.db.get_value("Delivery",self.delivery,"pointer_y")}"""))

			if res.status_code == 200:
				res = res.json()
				features = res.get("features",None)
				if features:
					geometry = features[0].get("geometry",None)
					if geometry:
						coordinations = geometry.get("coordinates" , [])
						if coordinations:
							coordinates = {
								"type":"FeatureCollection",
								"features":[
									{
										"type":"Feature",
										"properties":{},
										"geometry":{
											"type":"LineString",
											"coordinates":coordinations
										}
									}
								]
							}
							self.road_map = json.dumps(coordinates)
							frappe.db.commit()
					properties = features[0].get("properties",None)
					if properties:
						segments = properties.get("segments",None)
						if segments:
							distance = segments[0].get("distance",0)
							duration = segments[0].get("duration",0)
							self.duration  = format_duration(duration)
							self.total_distance = distance
			else:
				res = osm_v1(start_coordi,end_coordi)
				res = res.json()
				routes = res.get("routes")
				steps = routes[0].get("legs")[0].get("steps")
				locations = []
				for step in steps:
					for intersection in step["intersections"]:
						locations.append(intersection["location"])
						
				coordinates = {
					"type":"FeatureCollection",
					"features":[
						{
							"type":"Feature",
							"properties":{},
							"geometry":{
								"type":"LineString",
								"coordinates":locations
							}
						}
					]
				}
				self.road_map = json.dumps(coordinates)
				duration = routes[0].get("duration")
				# self.duration = float(duration or 0) / 60
				self.duration = format_duration(duration)
				self.total_distance = routes[0].get("distance")
				frappe.db.commit()


			
			
		if self.status in ['Delivered','Return to store']:
			self.finish_order()
	

	def change_request_status(self):
		status = []
		if self.request:
			if self.status in ["Delivered" , "Return to store"]:
				request = frappe.get_doc("Request Delivery", self.request)
				orders = request.get("order_request")

				for order in orders:
					if not order.order == self.name:
						status.append(frappe.get_value("Order", order.order, 'status'))
					status.append(self.status)
				if all(one in ['Delivered', 'Delivery Cancel', 'Store Cancel', "Return to store"] for one in status):
					request.status = "Delivered"
					request.save(ignore_permissions=True)
					frappe.db.commit()

			if self.status == "Cancel":
				request = frappe.get_doc("Request Delivery", self.request)
				orders = request.get("order_request")

				status = [frappe.get_value("Order", order.order, 'status') for order in orders if order.order != self.name]
				status.append(self.status)

				if all(element == 'Cancel' for element in status):
					# Update the status of the request if all are 'Cancel'
					request.status = "Cancel"
					request.save(ignore_permissions=True)
					frappe.db.commit()





	def begain_order(self):
		status = self.status
		self.append("order_log",{
			"status":status,
			"time": now_datetime(),
			"note":"Order Created"
		})

	def get_deduction(self):
		if self.status == "Arrived":
			self.late_after_accept()

		if self.status == "Cancel":
			self.if_order_cancelled_from_store_after_picked_up()
			self.if_order_cancelled_from_store_after_delivery_arrived()
		
		if self.status == "Picked":
			self.pick_up_deduction()


	def pick_up_deduction(self):
		# return True

		pick_up_deduction = Deductions.get("pick_up_deduction")
		order_logs = self.get("order_log")
		rate = 0
		if not order_logs or not pick_up_deduction:
			return
		time_difference = float(time_diff_in_seconds(now_datetime(), get_datetime(order_logs[-1].get("time")))) / 60
		row = next(
			(i for i in pick_up_deduction if i.get("from") < time_difference <= i.get("to")),
			None
		)

		try:
			rate = row.get("rate")
			if rate >= 100:
				request = frappe.get_doc("Request Delivery", self.request)
				request.status = "Store Cancel"
				request.save(ignore_permissions=True)
				frappe.db.commit()
		except Exception as e:
			frappe.log_error(f"Error while canceling request {self.request}: {str(e)}", "Pick Up Deduction Error")

		# self.status = "Cancel"
		# self.cancel_from = "Store"

		self.finish_order_with_rate(rate=rate / 100)



	
	def if_order_cancelled_from_store_after_picked_up(self):
		if self.cancel_from == "Store":
			order_logs = self.get("order_log")
			if order_logs:
				last_order_log = order_logs[-1]
				if last_order_log.get("status") == "Picked":
					self.finish_order_with_rate(rate=1.5)


	def if_order_cancelled_from_store_after_delivery_arrived(self):
		if self.cancel_from == "Store":
			order_logs = self.get("order_log")
			if order_logs:
				last_order_log = order_logs[-1]
				if last_order_log.get("status") == "Arrived":
					self.finish_order_with_rate(rate=1)


	def late_after_accept(self):
		return True
		order_logs = self.get("order_log")
		accepted_row = next((row for row in order_logs if row.get('status') == "Accepted"), None)
		if accepted_row:
			time_difference = time_diff_in_seconds(now_datetime(), get_datetime(accepted_row.get("time")))
			if float(time_difference or 0) / 60 > float(Deductions.late_after_accept or 0):
				self.status == "Cancel"
				self.cancel_from = "Delivery"
				self.finish_order_with_rate(rate=0.5)




	def get_previous_order_amount(self):
		if self.order_reference and self.order_type in ['Refund' , 'Replacing']:
			amount = frappe.get_value("Order",self.order_reference,'total_order')
			self.previous_order_amount = float(amount)
			self.the_rest_of_the_amount = float(self.total_order or 0) - float(amount)


	def calculate_duration(self):
		if self.get("order_log"):
			time = self.get("order_log")[-1].time
			datetime_obj1 = datetime.strptime(str(time), '%Y-%m-%d %H:%M:%S.%f')
			datetime_obj2 = datetime.strptime(str(now_datetime()), '%Y-%m-%d %H:%M:%S.%f')
			duration = datetime_obj2 - datetime_obj1
			seconds = duration.seconds
			minutes = (seconds % 3600) // 60
			if self.status == "Delivered":
				self.duration = float(minutes)
			return minutes

	def rate_delivery(self):
		if self.delivery:
			if self.valuation and frappe.db.exists("Delivery",self.delivery):
				del_obj = frappe.get_doc("Delivery" , self.delivery)
				del_obj.num_rates = float(del_obj.num_rates or 0) + 1
				del_obj.total_rates = float(del_obj.total_rates or 0) + float(self.valuation or 0)
				del_obj.save(ignore_permissions=True)


	def order_status(self):
		status = self.status
		note = ""
		if self.status == "Accepted":
			note = f"""Order Accepted in {now_datetime()}"""
		if self.status == "Arrived":
			note = f"""Delivary is Arrived to Store in {now_datetime()}"""
		if self.status == "Picked":
			note = f"""Order is Picked from Store in {now_datetime()}"""
		if self.status == "On The Way":
			note = f"""Order on the way to customer in {now_datetime()}"""
		if self.status == "Arrived For Destination":
			note = f"""the Driver Arrived For Destination in {now_datetime()}"""
		if self.status == "Delivered":
			note = f"""the Order is Delivered in {now_datetime()}"""
		if self.status == "Returned":
			note = f"""the Order is Returned in {now_datetime()}"""
		if self.status == "Delivery Cancel":
			note = f"""the Delivary Cancel this order in {now_datetime()}"""
		if self.status == "Store Cancel":
			note = f"""the Store Cancel this order in {now_datetime()}"""
		if self.status == "Cancel":
			note = f"""the Order Canceled this order in {now_datetime()}"""
		if self.status != 'Pending':
			self.append("order_log",{
				"status":status,
				"time": now_datetime(),
				"note": note
			})


	def finish_order(self):
		amount = 0
		total = 0

		if self.delivery:
			if frappe.db.exists("Delivery Category" , frappe.get_value("Delivery" , self.delivery , 'delivery_category')):
				delivery_category = frappe.get_doc(
					"Delivery Category" , 
					frappe.get_value("Delivery" , self.delivery , 'delivery_category')
				)
				amount = (float(self.total_distance) / 1000) * float(delivery_category.rate_of_km or 0) 
				if delivery_category.minimum_rate > amount:
					total = float(delivery_category.minimum_rate or 0) if self.status == "Delivered" else float(delivery_category.minimum_rate or 0) * float(Deductions.rate2 or 1)
				else:
					total = amount if self.status == "Delivered" else float(amount or 0) * float(Deductions.rate2 or 1)
				total = total - (total / 100 * self.discount)
				self.delivery_fees = total
				tax = frappe.db.get_single_value('Deductions', 'rate_of_tax')
				# tax_rate = float(tax or 0) / total
				tax_rate = (total * tax / 100)
				self.tax = tax_rate
				total = total - tax_rate 

				
				self.net_delivery_fees = total

				

				doc = frappe.new_doc("Transactions")
				doc.party = "Delivery"
				doc.party_type = self.delivery
				doc.in_wallet = total
				doc.aganist = "Store"
				doc.aganist_from = self.store
				doc.order = self.name
				doc.save(ignore_permissions=True)
				doc.submit()
		
		if self.store:
			store = frappe.get_doc("Store" , self.store)
			amount = (float(self.total_distance) / 1000) * float(store.rate_of_km or 0) 
			if store.minimum_price > amount:
				total = float(store.minimum_price or 0) if self.status == "Delivered" else float(store.minimum_price or 0) * float(Deductions.rate2 or 1)
			else:
				total = amount if self.status == "Delivered" else float(amount or 0) * float(Deductions.rate2 or 1)
			self.store_fees = total
			total = total - (total / 100 * self.discount)
			self.net_store_fees = total

			doc = frappe.new_doc("Transactions")
			doc.party = "Store"
			doc.party_type = self.store
			doc.out = total
			doc.aganist = "Delivery"
			doc.aganist_from = self.delivery
			doc.order = self.name
			doc.save(ignore_permissions=True)
			doc.submit()
		frappe.db.commit()


		store = {
			"account_credit": Deductions.light_account,
			"amount_credit":self.net_store_fees,

			"account_debit": Deductions.store_account,
			"party_type_debit": "Customer",
			"party_debit": frappe.get_value("Store",self.store,'username'),
			"amount_debit": self.net_store_fees,

			"order":self.name
			}
		if self.net_store_fees > 0:
			make_journal_entry(store)


		delivery = {
			"account_debit": Deductions.expens_account,
			"amount_debit": self.delivery_fees,

			"account_credit": Deductions.delivery_account,
			"party_type_credit": "Supplier",
			"party_credit": frappe.get_value("Delivery",self.delivery,'delivery_name'),
			"amount_credit":self.delivery_fees ,	

			"order":self.name
			}
		
		if self.delivery_fees > 0 :
			make_journal_entry(delivery)

		prof_delivery = {
			"account_debit": Deductions.delivery_account,
			"party_type_debit": "Supplier",
			"party_debit": frappe.get_value("Delivery",self.delivery,'delivery_name'),
			"amount_debit":self.delivery_fees,

			"account_credit": Deductions.balance,
			"party_type_credit": "Supplier",
			"party_credit": frappe.get_value("Delivery",self.delivery,'delivery_name'),
			"amount_credit":self.delivery_fees,	

			"order":self.name
			}
		if self.delivery_fees > 0:
			make_journal_entry(prof_delivery)
		
		tax = {
			"account_credit": Deductions.tax_account,
			"amount_credit": self.tax,

			"account_debit": Deductions.balance,
			"party_type_debit": "Supplier",
			"party_debit": frappe.get_value("Delivery",self.delivery,'delivery_name'),
			"amount_debit":self.tax,

			"order":self.name
			}
		if self.tax > 0 :
			make_journal_entry(tax)

	def finish_order_with_rate(self , rate ):
		amount = 0
		total = 0

		if self.delivery:
			if frappe.db.exists("Delivery Category" , frappe.get_value("Delivery" , self.delivery , 'delivery_category')):
				delivery_category = frappe.get_doc(
					"Delivery Category" , 
					frappe.get_value("Delivery" , self.delivery , 'delivery_category')
				)

				total = float(delivery_category.minimum_rate or 0) * rate

				total =(total - (total / 100 * self.discount))
				self.delivery_fees = total 
				tax = frappe.db.get_single_value('Deductions', 'rate_of_tax')
				tax_rate = (total * tax / 100)
				self.tax = tax_rate
				total = total - tax_rate 

				
				self.net_delivery_fees = total

				

				doc = frappe.new_doc("Transactions")
				doc.party = "Delivery"
				doc.party_type = self.delivery
				doc.in_wallet = total
				doc.aganist = "Store"
				doc.aganist_from = self.store
				doc.order = self.name
				doc.save(ignore_permissions=True)
				doc.submit()
		
		if self.store:
			store = frappe.get_doc("Store" , self.store)

			total = float(store.minimum_price or 0) * rate
			
			self.store_fees = total
			total = total - (total / 100 * self.discount)
			self.net_store_fees = total

			doc = frappe.new_doc("Transactions")
			doc.party = "Store"
			doc.party_type = self.store
			doc.out = total
			doc.aganist = "Delivery"
			doc.aganist_from = self.delivery
			doc.order = self.name
			doc.save(ignore_permissions=True)
			doc.submit()
		frappe.db.commit()


		store = {
			"account_credit": Deductions.light_account,
			"amount_credit":self.net_store_fees,

			"account_debit": Deductions.store_account,
			"party_type_debit": "Customer",
			"party_debit": frappe.get_value("Store",self.store,'username'),
			"amount_debit": self.net_store_fees,

			"order":self.name
			}
		if self.net_store_fees > 0:
			make_journal_entry(store)


		delivery = {
			"account_debit": Deductions.expens_account,
			"amount_debit": self.delivery_fees,

			"account_credit": Deductions.delivery_account,
			"party_type_credit": "Supplier",
			"party_credit": frappe.get_value("Delivery",self.delivery,'delivery_name'),
			"amount_credit":self.delivery_fees ,	

			"order":self.name
			}
		
		if self.delivery_fees > 0 :
			make_journal_entry(delivery)

		prof_delivery = {
			"account_debit": Deductions.delivery_account,
			"party_type_debit": "Supplier",
			"party_debit": frappe.get_value("Delivery",self.delivery,'delivery_name'),
			"amount_debit":self.delivery_fees,

			"account_credit": Deductions.balance,
			"party_type_credit": "Supplier",
			"party_credit": frappe.get_value("Delivery",self.delivery,'delivery_name'),
			"amount_credit":self.delivery_fees,	

			"order":self.name
			}
		if self.delivery_fees > 0:
			make_journal_entry(prof_delivery)
		
		tax = {
			"account_credit": Deductions.tax_account,
			"amount_credit": self.tax,

			"account_debit": Deductions.balance,
			"party_type_debit": "Supplier",
			"party_debit": frappe.get_value("Delivery",self.delivery,'delivery_name'),
			"amount_debit":self.tax,

			"order":self.name
			}
		if self.tax > 0 :
			make_journal_entry(tax)
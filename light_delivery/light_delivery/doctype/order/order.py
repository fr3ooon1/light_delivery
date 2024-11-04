# Copyright (c) 2024, Muhammad Essam and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
import json
from frappe.utils import now_datetime
from light_delivery.api.apis import calculate_distance_and_duration , haversine
from datetime import datetime


class Order(Document):
	def before_naming(self):
		self.begain_order()


	def validate(self):
		self.draw_roads()
		self.get_deduction()
		self.order_status()
		self.get_previous_order_amount()
		self.rate_delivery()
		self.change_request_status()
		road(self)	

	

	def change_request_status(self):
		status = []
		if self.request:
			if self.status == "Delivered":
				request = frappe.get_doc("Request Delivery", self.request)
				orders = request.get("order_request")

				for order in orders:
					if not order.order == self.name:
						status.append(frappe.get_value("Order", order.order, 'status'))
					status.append(self.status)
				if all(one in ['Delivered', 'Delivery Cancel', 'Store Cancel'] for one in status):
					request.status = "Delivered"
					request.save(ignore_permissions=True)
					frappe.db.commit()

			if self.status == "Cancel":
				request = frappe.get_doc("Request Delivery", self.request)
				orders = request.get("order_request")

				status = [frappe.get_value("Order", order.order, 'status') for order in orders if order.order != self.name]
				status.append(self.status)
				print(status)

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
		return True
		minutes = float(self.calculate_duration())
		deduction_obj = frappe.get_doc("Deductions")
		
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


	def draw_roads(self):
		temp = 0
		total = 0
		counter = 0
		distance = 0
		if self.status in ['Returned' , 'Delivered']:
			road = self.get('road')
			if not road or len(road) < 2:
				message = "Insufficient road data to calculate distance."
				print(message)
				self.total_distance = 0
				return message
			

			# for idx in range(len(road)-1):
			# 	first_point = [float(road[idx].get("pointer_x")), float(road[idx].get("pointer_y"))]
				
			# 	end_point = [float(road[idx+1].get("pointer_x") ), float(road[idx+1].get("pointer_y"))]
			# 	counter = haversine(first_point,end_point)
			# 	distance += counter
			# total_distance = float(distance)
			# self.total_distance = total_distance

			# if self.delivery:
			# 	if frappe.db.exists("Delivery Category" , frappe.get_value("Delivery" , self.delivery , 'delivery_category')):
			# 		delivery_category = frappe.get_doc("Delivery Category" , frappe.get_value("Delivery" , self.delivery , 'delivery_category'))
			# 		temp = total_distance * float(delivery_category.rate_of_km or 0) 
			# 		if delivery_category.minimum_rate > temp:
			# 			total = float(delivery_category.minimum_rate or 0)
			# 		else:
			# 			total = temp
			# 		total = total - (total / 100 * self.discount)
			# 		tax = frappe.db.get_single_value('Deductions', 'rate_of_tax')
			# 		tax_rate = float(tax or 0) / total
			# 		self.tax = tax_rate
			# 		total = total - tax_rate 

			# 		self.delivery_fees = total

					

			# 		doc = frappe.new_doc("Transactions")
			# 		doc.party = "Delivery"
			# 		doc.party_type = self.delivery
			# 		doc.in_wallet = total
			# 		doc.aganist = "Store"
			# 		doc.aganist_from = self.store
			# 		doc.order = self.name
			# 		doc.save(ignore_permissions=True)
			# 		doc.submit()
			
			# if self.store:
			# 	store = frappe.get_doc("Store" , self.store)
			# 	temp = total_distance * float(store.rate_of_km or 0) 
			# 	if store.minimum_price > temp:
			# 		total = float(store.minimum_price or 0)
			# 	else:
			# 		total = temp
			# 	total = total - (total / 100 * self.discount)
			# 	self.store_fees = total

			# 	doc = frappe.new_doc("Transactions")
			# 	doc.party = "Store"
			# 	doc.party_type = self.store
			# 	doc.out = total
			# 	doc.aganist = "Delivery"
			# 	doc.aganist_from = self.delivery
			# 	doc.order = self.name
			# 	doc.save(ignore_permissions=True)
			# 	doc.submit()

			# frappe.db.commit()

			# coord = []
			# if road:
			# 	for i in road:
			# 		coord.append([float(i.pointer_x),float(i.pointer_y)])
			# 	coordinates = {
			# 		"type":"FeatureCollection",
			# 		"features":[
			# 			{
			# 				"type":"Feature",
			# 				"properties":{},
			# 				"geometry":{
			# 					"type":"LineString",
			# 					"coordinates":coord
			# 				}
			# 			}
			# 		]
			# 	}
			# 	self.road_map = json.dumps(coordinates)
			# 	# self.save()
			# 	frappe.db.commit()
def road(self):
	if self.status == "On The Way":
		self.start_lat = float(frappe.db.get_value("Delivery",self.delivery,"pointer_x"))
		self.start_lon = float(frappe.db.get_value("Delivery",self.delivery,"pointer_y"))

	if self.status == "Delivered":
		self.end_lat = float(frappe.db.get_value("Delivery",self.delivery,"pointer_x"))
		self.end_lon = float(frappe.db.get_value("Delivery",self.delivery,"pointer_y"))

		start_coordi = [float(self.start_lon) , float(self.start_lat)]
		end_coordi = [float(frappe.db.get_value("Delivery",self.delivery,"pointer_x")) , float(frappe.db.get_value("Delivery",self.delivery,"pointer_y"))]


		res = calculate_distance_and_duration(start_coordi,end_coordi)
		print(res)
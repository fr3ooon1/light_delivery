# Copyright (c) 2024, Muhammad Essam and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
import json
from frappe.utils import now_datetime
from light_delivery.api.apis import calculate_distance_and_duration , haversine


class Order(Document):
	def before_naming(self):
		self.begain_order()


	def validate(self):
		self.draw_roads()
		self.order_status()


	def begain_order(self):
		status = self.status
		self.append("order_log",{
			"status":status,
			"time": now_datetime(),
			"note":"Order Created"
		})

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
			for idx in range(len(road)-1):
				first_point = [float(road[idx].get("pointer_x")), float(road[idx].get("pointer_y"))]
				
				end_point = [float(road[idx+1].get("pointer_x") ), float(road[idx+1].get("pointer_y"))]
				counter = haversine(first_point,end_point)
				distance += counter
			total_distance = float(distance)
			self.total_distance = total_distance

			if self.delivery:
				if frappe.db.exists("Delivery Category" , frappe.get_value("Delivery" , self.delivery , 'delivery_category')):
					delivery_category = frappe.get_doc("Delivery Category" , frappe.get_value("Delivery" , self.delivery , 'delivery_category'))
					temp = total_distance * float(delivery_category.rate_of_km or 0) 
					if delivery_category.minimum_rate > temp:
						total = float(delivery_category.minimum_rate or 0)
						total = total - (total / 100 * self.discount)
					else:
						total = temp
						total = total - (total / 100 * self.discount)
					self.delivery_fees = total

					

					doc = frappe.new_doc("Transactions")
					doc.party = "Delivery"
					doc.party_type = self.delivery
					doc.in_wallet = total
					doc.aganist = "Store"
					doc.aganist_from = self.store
					doc.save(ignore_permissions=True)
					doc.submit()
			
			if self.store:
				store = frappe.get_doc("Store" , self.store)
				temp = total_distance * float(store.rate_of_km or 0) 
				if store.minimum_price > temp:
					total = float(store.minimum_price or 0)
				else:
					total = temp
				self.store_fees = total

				doc = frappe.new_doc("Transactions")
				doc.party = "Store"
				doc.party_type = self.store
				doc.out = total
				doc.aganist = "Delivery"
				doc.aganist_from = self.delivery
				doc.save(ignore_permissions=True)
				doc.submit()

			frappe.db.commit()

			coord = []
			if road:
				for i in road:
					coord.append([float(i.pointer_x),float(i.pointer_y)])
				coordinates = {
					"type":"FeatureCollection",
					"features":[
						{
							"type":"Feature",
							"properties":{},
							"geometry":{
								"type":"LineString",
								"coordinates":coord
							}
						}
					]
				}
				self.road_map = json.dumps(coordinates)
				# self.save()
				frappe.db.commit()
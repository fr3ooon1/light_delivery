# Copyright (c) 2024, Muhammad Essam and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
import json
from frappe.utils import now_datetime


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
		
		if self.status in ['Returned' , 'Delivered']:
			road = self.get('road')
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
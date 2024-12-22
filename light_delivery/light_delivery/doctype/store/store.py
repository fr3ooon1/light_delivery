# Copyright (c) 2024, Muhammad Essam and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
import json


class Store(Document):
	def validate(self):
		self.draw_location()
		self.validate_price_list()
	
	def draw_location(self):
		if self.pointer_x and self.pointer_y:
			coordi = [float(self.pointer_x) , float(self.pointer_y)]
			coordinates = {
					"type":"FeatureCollection",
					"features":[
						{
							"type":"Feature",
							"properties":{},
							"geometry":{
								"type":"Point",
								"coordinates":coordi
							}
						}
					]
				}
			self.store_location = json.dumps(coordinates)
			frappe.db.commit()

	def validate_price_list(self):
		if self.status == 'Active':
			if self.minimum_price == 0 or self.rate_of_km == 0:
				frappe.throw(_("Please select price list"))
		
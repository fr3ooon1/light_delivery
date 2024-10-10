# Copyright (c) 2024, Muhammad Essam and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import json


class Store(Document):
	def validate(self):
		self.draw_location()
	
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
			self.delivery_location = json.dumps(coordinates)
			frappe.db.commit()
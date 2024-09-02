# Copyright (c) 2024, Muhammad Essam and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
import json


class Order(Document):
	def on_change(self):
		self.draw_roads()

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
				frappe.db.commit()
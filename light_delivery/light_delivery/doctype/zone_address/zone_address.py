# Copyright (c) 2024, Muhammad Essam and contributors
# For license information, please see license.txt

import frappe
from frappe import _
import json
from frappe.model.document import Document


class ZoneAddress(Document):
	def validate(self):
		self.drow_radius()
		self.validate_geolocation()


	def drow_radius(self):
		if self.x and self.y:
			data = {
				"type":"FeatureCollection",
				"features":[
					{
						"type":"Feature",
						"properties":{
							"point_type":"circle",
							"radius":2000
						},
						"geometry":{
							"type":"Point","coordinates":[float(self.y or 0),float(self.x or 0)]}}]}
			self.geolocation_klnh = json.dumps(data)


	def validate_geolocation(self):
		if not self.geolocation_klnh:
			frappe.throw(_("Geolocation is required"))
		geolocation_klnh = json.loads(self.geolocation_klnh)
		if not geolocation_klnh.get("features"):
			frappe.throw(_("Geolocation is required"))

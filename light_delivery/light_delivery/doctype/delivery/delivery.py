# Copyright (c) 2024, Muhammad Essam and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime
from frappe.utils import now_datetime
import json




class Delivery(Document):
	def validate(self):
		self.draw_location()
		self.rate_delivery()
	
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

	def rate_delivery(self):
		if self.total_retes:
			rate = float(self.total_rates or 0) / float(self.num_rates or 0)
			self.valuation = rate



# from light_delivery.light_delivery.doctype.delivery.delivery import update_delivery_category
@frappe.whitelist()
def update_delivery_category():
	try:
		today = now_datetime()
		today_day = today.day
		end = frappe.utils.add_months(today, -1)
		day_in_month_before = frappe.utils.add_days(end, 1)

		deliverys = frappe.db.sql(f"""
			SELECT name
			FROM `tabDelivery`
			WHERE DAY(date_of_joining) = {today_day}
		""", as_dict=1)

		for delivery in deliverys:
			orders_num = frappe.db.count("Order", {
				"delivery": delivery.get('name'),
				"order_date": ["between", [day_in_month_before, today]]
			})
			new_category = frappe.db.sql(f"""
				SELECT name
				FROM `tabDelivery Category`
				WHERE minimum_orders <= {orders_num} AND maximum_orders >= {orders_num}
			""", pluck='name')

			if new_category:
				print(delivery.get('name'), new_category[0])

				# frappe.db.set_value("Delivery" , delivery.get('name') , 'delivery_category' , new_category[0] )
				doc = frappe.get_doc("Delivery", delivery.get('name'))
				doc.delivery_category = new_category[0]
				doc.save()
				frappe.db.commit()

		return {"status": "success", "message": "Delivery categories updated successfully."}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "update_delivery_category")
		return {"status": "error", "message": str(e)}

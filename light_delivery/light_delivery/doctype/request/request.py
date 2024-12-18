# Copyright (c) 2024, Muhammad Essam and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class Request(Document):
	def validate(self):
		self.validation()
		self.accepted_delivery()
		
	
	def accepted_delivery(self):
		if self.status in ["Accepted","Cancel","Store Cancel" , "Delivery Cancel"]:
			doc = frappe.get_doc("Request Delivery" , self.request_delivery)
			doc.delivery = self.delivery
			
			doc.lat = frappe.get_value("Delivery",self.delivery,'pointer_x')
			doc.lon = frappe.get_value("Delivery",self.delivery,'pointer_y')
			
			doc.status = self.status

			for order in doc.order_request:
				order_obj = frappe.get_doc("Order",order.get("order"))
				order_obj.delivery = self.delivery
				order_obj.save(ignore_permissions=True)
				frappe.db.commit()
			doc.save(ignore_permissions=True)
			frappe.db.commit()
	
	def validation(self):
		delivery_request_status = frappe.get_value("Request Delivery",self.request_delivery,'status')
		if self.status in ['Accepted','Store Cancel','Delivery Cancel','Cancel']:
			if delivery_request_status != "Waiting for delivery":
				frappe.throw("The Request Take an action before")
 

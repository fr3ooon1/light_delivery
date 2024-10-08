# Copyright (c) 2024, Muhammad Essam and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class Request(Document):
	def validate(self):
		self.accepted_delivery()
	
	def accepted_delivery(self):
		if self.status == "Accepted":
			doc = frappe.get_doc("Request Delivery" , self.request_delivery)
			doc.delivery = self.delivery
			doc.status = "Accepted"

			for order in doc.order_request:
				order_obj = frappe.get_doc("Order",order.get("order"))
				order_obj.delivery = self.delivery
				order_obj.save(ignore_permissions=True)
				frappe.db.commit()
			doc.save(ignore_permissions=True)
			frappe.db.commit()


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
			# delivery = self.get("deliveries")[0].get("delivery")
			# self.delivery = delivery
			doc.delivery = self.delivery
			doc.status = "Accepted"
			doc.save(ignore_permissions=True)
			frappe.db.commit()


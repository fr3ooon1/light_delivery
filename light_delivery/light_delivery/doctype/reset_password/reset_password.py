# Copyright (c) 2024, Muhammad Essam and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ResetPassword(Document):
	def autoname(self):
		generate_name = frappe.generate_hash(length=8)
		self.name = generate_name


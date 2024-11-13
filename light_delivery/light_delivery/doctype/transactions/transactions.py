# Copyright (c) 2024, Muhammad Essam and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from light_delivery.api.delivery_request import get_balance


class Transactions(Document):
	def before_naming(self):
		self.calculate_balance()


	def calculate_balance(self):
		first_name = frappe.get_value("User",{"username":self.party_type},'first_name')
		if self.get("in_wallet"):
			self.balance =  float(get_balance(first_name) or 0) + self.get('in_wallet') or 0
		if self.get("out"):
			self.balance =  float(get_balance(first_name) or 0) - self.get('out') or 0
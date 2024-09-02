# Copyright (c) 2024, Muhammad Essam and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from light_delivery.api.delivery_request import calculate_balane


class Transactions(Document):
	def before_naming(self):
		self.calculate_balance()


	def calculate_balance(self):
		if self.get("in_wallet"):
			self.balance =  float(calculate_balane(self.party_type)) + self.get('in_wallet')
		if self.get("out"):
			self.balance =  float(calculate_balane(self.party_type)) - self.get('out')
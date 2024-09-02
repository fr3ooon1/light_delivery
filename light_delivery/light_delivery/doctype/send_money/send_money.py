# Copyright (c) 2024, Muhammad Essam and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from light_delivery.api.delivery_request import calculate_balane


class SendMoney(Document):
	def validate(self):
		self.check_balance()
	def on_submit(self):
		self.create_transaction()

	def check_balance(self):
		if float(calculate_balane(self.party_type)) < self.amount:
			frappe.throw("Can not send Money because your balance is less than amount")
	def create_transaction(self):
		doc = frappe.new_doc("Transactions")
		doc.party = self.party
		doc.party_type = self.party_type
		doc.out = self.amount
		doc.aganist = self.against
		doc.aganist_from = self.against_type
		doc.save(ignore_permissions=True)
		doc.submit()

		doc2 = frappe.new_doc("Transactions")
		doc2.party = self.against
		doc2.party_type = self.against_type
		doc2.in_wallet = self.amount
		doc2.aganist = self.party
		doc2.aganist_from = self.party_type
		doc2.save(ignore_permissions=True)
		doc2.submit()
		frappe.db.commit()

# Copyright (c) 2024, Muhammad Essam and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Closingoperations(Document):
	def on_submit(self):
		self.create_transaction()


	def create_transaction(self):
		doc = frappe.new_doc("Transactions")
		doc.party = self.party
		doc.party_type = self.party_type
		if float(self.amount) > 0 :
			doc.out = self.amount
		else:
			doc.in_wallet = self.amount
		doc.save(ignore_permissions=True)
		frappe.db.commit()
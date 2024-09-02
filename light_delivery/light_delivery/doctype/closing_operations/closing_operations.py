# Copyright (c) 2024, Muhammad Essam and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Closingoperations(Document):
	pass



@frappe.whitelist()
def calculate_amount(party_type):
	pass
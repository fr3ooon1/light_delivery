# Copyright (c) 2024, Muhammad Essam and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from light_delivery.api.delivery_request import calculate_balane
from erpnext import get_default_company
from frappe.utils import nowdate 


class Closingoperations(Document):
	def validate(self):
		self.make_balance_table()
	def on_submit(self):
		self.create_transaction()

	
	def make_balance_table(self):
		balance = calculate_balane(self.party_type)

		company = get_default_company()

		default_receivable_account = frappe.get_value("Company",company,'default_receivable_account',)
		default_income_account = frappe.get_value("Company",company,'default_income_account')
		if balance > 0:
			self.append("accounts",{
					"account":default_receivable_account,
					"party_type": "Customer",
					"party": "Palmer Productions Ltd.",
					"debit_in_account_currency":balance,
					"credit_in_account_currency":0
				})
			self.append("accounts",{
					"account":default_income_account,
					# "party_type": "Customer",
					# "party": "Palmer Productions Ltd.",
					"debit_in_account_currency":0,
					"credit_in_account_currency":balance
				})
		else:
			self.append("accounts",{
					"account":default_receivable_account,
					# "party_type": "Customer",
					# "party": "Palmer Productions Ltd.",
					"debit_in_account_currency":balance,
					"credit_in_account_currency":0
				})
			self.append("accounts",{
					"account":default_income_account,
					"party_type": "Customer",
					"party": "Palmer Productions Ltd.",
					"debit_in_account_currency":0,
					"credit_in_account_currency":balance
				})

	def create_transaction(self):
		doc = frappe.new_doc("Transactions")
		doc.party = self.party
		doc.party_type = self.party_type
		if float(self.amount) > 0 :
			doc.out = self.amount
		else:
			doc.in_wallet = abs(self.amount)
		doc.paid = 1
		doc.save(ignore_permissions=True)
		doc.submit()
		frappe.db.commit()


		transactions = frappe.get_list(
			"Transactions", 
			{
				"party_type": self.party_type , 
				"paid": 0
			})
		if transactions:
			for i in transactions:
				if frappe.db.exists("Transactions" , i.name):
					frappe.db.set_value("Transactions" , i.name , 'reference' , self.name)
					frappe.db.set_value("Transactions" , i.name , 'paid' , 1)
		
# from frappe.model.mapper import get_mapped_doc

@frappe.whitelist()
def create_sales_invoice(doc):
	self = frappe.get_doc("Closing operations" , doc)
	doc = frappe.new_doc("Sales Invoice")
	doc.customer = "Grant Plastics Ltd."
	doc.posting_date = self.due_date
	doc.due_date = self.due_date
	doc.append("items",{
					"item_code":"test",
					"qty":1,
					"rate":abs(self.amount)
				})
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	frappe.db.set_value("Closing operations",self.name,"invoice_reference",doc.name)
	frappe.msgprint("Sales Invoice Created"+doc.name)
	return doc.name







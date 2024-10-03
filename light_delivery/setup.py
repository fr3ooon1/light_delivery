import frappe
import os
import json

def after_install():
	print("Light Delivery Mobile App")
	create_domain_list()
	

def create_domain_list():
	if not frappe.db.exists("Domain", "Light Delivery"):
		dm1 = frappe.new_doc("Domain")
		dm1.domain = 'Light Delivery'
		dm1.insert()
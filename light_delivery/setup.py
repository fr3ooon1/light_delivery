import frappe
import os
import json

def after_install():
	print("Light Delivery Mobile App")
	create_domain_list()
	create_customer_groups()
	

def create_domain_list():
	if not frappe.db.exists("Domain", "Light Delivery"):
		dm1 = frappe.new_doc("Domain")
		dm1.domain = 'Light Delivery'
		dm1.insert()



def create_customer_groups():
	if not frappe.db.exists("Customer Group","Delivery"):
		delivery = frappe.new_doc("Customer Group")
		delivery.customer_group_name = "Delivery"
		delivery.insert(ignore_permissions=True)

	if not frappe.db.exists("Customer Group","Store"):
		store = frappe.new_doc("Customer Group")
		store.customer_group_name = "Store"
		store.insert(ignore_permissions=True)

	if not frappe.db.exists("Customer Group","End User"):
		end_user = frappe.new_doc("Customer Group")
		end_user.customer_group_name = "End User"
		end_user.insert(ignore_permissions=True)
	
import frappe
import os
import json

def after_install():
	print("Light Delivery Mobile App")
	create_domain_list()
	create_customer_groups()
	create_status()
	

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
	
	if not frappe.db.exists("Customer Group","Consumer"):
		end_user = frappe.new_doc("Customer Group")
		end_user.customer_group_name = "Consumer"
		end_user.insert(ignore_permissions=True)
	

def create_status():
	status = [
		{
			"status":"Pending",
			"status_name_in_arabic":"قيد الانتظار",
			"index":1
		},
		{
			"status":"Accetped",
			"status_name_in_arabic":"مقبول",
			"index":2
		},
		{
			"status":"Arrived",
			"status_name_in_arabic":"وصل",
			"index":3
		},
		{
			"status":"Picked",
			"status_name_in_arabic":"تم التقاط الطلب",
			"index":4
		},
		{
			"status":"On The Way",
			"status_name_in_arabic":"في الطريق",
			"index":5
		},
		{
			"status":"Arrived For Destination",
			"status_name_in_arabic":"وصول إلى الوجهة",
			"index":6
		},
		{
			"status":"Delivered",
			"status_name_in_arabic":"تم التوصيل",
			"index":7
		},
		{
			"status":"Refused",
			"status_name_in_arabic":"رفض",
			"index":8
		},
		{
			"status":"Return to store",
			"status_name_in_arabic":"العودة إلى المتجر",
			"index":9
		},
		{
			"status":"Cancel",
			"status_name_in_arabic":"تم الإلغاء",
			"index":10
		},
	]
	for i in status:
		if not frappe.db.exists("Status",i.get("status")):
			status = frappe.new_doc("Status")
			status.status = i.get("status")
			status.status_name_in_arabic = i.get("status_name_in_arabic")
			status.index = str(i.get("index"))
			status.insert(ignore_permissions=True)


@frappe.whitelist(allow_guest=True)
def get_all_status():
    types = frappe.get_list("Order Type", fields=["name"])
    all_status = []
    
    for i in types:
        status = frappe.db.sql(f"""
            SELECT 
				s.index,
                ots.status as en,
                s.status_name_in_arabic as ar
            FROM 
                `tabOrder Type Status` ots
            JOIN
                `tabStatus` s
            ON
                ots.status = s.name
            WHERE 
                ots.parent = '{i.name}'""", as_dict=1)

        all_status.append({
            "order_type": i.name,
            "status": status
        })
    return all_status



@frappe.whitelist()
def get_status(index):
	if frappe.db.exists("Status",{"index":index}):
		return {
			"en":frappe.get_value("Status",{"index":index}),
			"ar":frappe.get_value("Status",{"index":index},'status_name_in_arabic')
		}
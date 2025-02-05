# Copyright (c) 2025, Muhammad Essam and contributors
# For license information, please see license.txt

import json
import requests
import frappe
from frappe import _
from light_delivery.api.apis import get_url
from frappe.model.document import Document


class Notifications(Document):
	pass


@frappe.whitelist()
def send_notification(doc):
	doc = frappe.get_doc("Notifications", doc)
	if doc.send_to_particular_segments:
		notification_id = frappe.get_value("User",doc.user,"notification_key")
		message = send_message([notification_id] , doc.message , doc.title , doc.heading , doc.launch_url , doc.image ) 
		if message.status_code == 200:
			frappe.msgprint("Notification Sent Successfully")
		else:
			frappe.msgprint("Notification Not Sent Successfully")
			frappe.msgprint(message.text)
			frappe.log_error(message.text, "Notification Not Sent Successfully")

	if doc.send_to:
		notification_ids = get_notification_id(doc)
		message = send_message(notification_ids , doc.message , doc.title , doc.heading , doc.launch_url , doc.image )
		if message.status_code == 200:
			frappe.msgprint("Notification Sent Successfully")
		else:
			frappe.msgprint("Notification Not Sent Successfully")
			frappe.msgprint(message.text)
			frappe.log_error(message.text, "Notification Not Sent Successfully")


@frappe.whitelist()
def send_message(UsersArray , message , title , heading ,  url , image):

	image = f"{get_url()}{image}"
	# payload = {
	# 	"app_id": "e75df22c-56df-4e69-8a73-fc80c73c4337",
	# 	"headings": { 
	# 		"en": heading
	# 	},
	# 	"title": { 
	# 		"en": title
	# 	},
	# 	"contents": { 
	# 		"en": message
	# 	},
	# 	"include_player_ids": UsersArray,
	# 	"url":url,
	# 	"global_image":image,
	# 	"big_picture":image,
	# 	"large_icon":image,
	# 	"android_image":image,

	# }
	payload = {
		"app_id": "e75df22c-56df-4e69-8a73-fc80c73c4337",
		"headings": { "en": heading },
		"title": { "en": title },
		"contents": { "en": message },
		"include_player_ids": UsersArray,
		"url": url,
		"big_picture": image,
		"chrome_big_picture": image,
		"ios_attachments": { "image": image },
	}	

	url = "https://onesignal.com/api/v1/notifications"

	headers = {
		"Content-Type": "application/json; charset=utf-8",
		"Authorization": "Basic NmMwNGNmM2MtYzM5Zi00ODYwLTk0ODYtYWNiMDlkY2M2NDFi"
	}
	print(payload)
	payload_json = json.dumps(payload)

	response = requests.post(url, headers=headers, data=payload_json)
	print(f"{response.text} , {response.status_code}")
	return response


@frappe.whitelist()
def get_notification_id(doc):
	notification_ids = []
	users = {}
	if doc.party_type == "Store":
		if not doc.zone_address :
			frappe.throw(_("Please Select Zone Address"))
			return
		
		users = frappe.get_list("Store",{"zone":doc.zone_address},['name','user'],ignore_permissions=True)
		for user in users:
			notification_id = frappe.get_value("User",user.get("user"),"notification_key")
			notification_ids.append(notification_id)

	if doc.party_type == "Customer":
		if not doc.zone_address:
			frappe.throw(_("Please select zone Address"))
			return
		users = frappe.get_list("Customer",{"customer_group":"Consumer"},['name'])
		for user in users:
			notification_id = frappe.get_value("User",{"username":user.get("user")},"notification_key")
			notification_ids.append(notification_id)
	
	if doc.party_type == "Delivery":
		if not doc.delivery_category:
			frappe.throw(_("Please select Delivery Category"))
			return
		users = frappe.get_list("Delivery",{"delivery_category":doc.delivery_category},['name','user'])
		for user in users:
			notification_id = frappe.get_value("User",user.get("user"),"notification_key")
			notification_ids.append(notification_id)

	print(notification_ids)
	return notification_ids



@frappe.whitelist()
def get_segments():
	url = "https://onesignal.com/api/v1/apps/e75df22c-56df-4e69-8a73-fc80c73c4337/segments"
	headers = {
		"Content-Type": "application/json; charset=utf-8",
		"Authorization": "Basic NmMwNGNmM2MtYzM5Zi00ODYwLTk0ODYtYWNiMDlkY2M2NDFi"
	}
	response = requests.get(url, headers=headers)
	return response.json()

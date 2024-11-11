import frappe
from frappe import _
import os
import base64
import math
import requests
import json

#from light_delivery.api.apis import

@frappe.whitelist(allow_guest = False)
def search_delivary(cash , store = None ):
	try:
		if not store:
			store = frappe.get_value("Store",{'user',frappe.session.user})
		if frappe.db.exists("Store",store):
			store = frappe.get_doc("Store" ,store)
			store_location = json.loads(store.store_location)
			store_coord = store_location.get("features")[0].get("geometry").get("coordinates")

			deliveries = frappe.db.sql(f"""
									select 
										d.name as name , d.user as user , d.pointer_x as pointer_x , d.pointer_y as pointer_y , u.notification_key as notification_key
									from 
										`tabDelivery` d
							  		join 
							  			`tabUser` u
							  		on 
							  			d.user = u.name
									where 
										status = 'Avaliable' and cash >= {cash} """, as_dict=1)
			distance = []
			for delivery in deliveries:
				if delivery['pointer_x'] is not None and delivery['pointer_y'] is not None:
					del_coord = [float(delivery['pointer_x']), float(delivery['pointer_y'])]

					dist = float(haversine(coord1=del_coord, coord2=store_coord) or 0) * 1000
					delivery_data = {
						'distance': dist,
						'user': delivery.get('user'),
						'name': delivery.get('name'),
						'coordination': del_coord ,
						'notification_key' : delivery.get("notification_key")
					}
					distance.append(delivery_data)
			sorted_deliveries = sorted(distance, key=lambda x: x['distance'])
			result = [entry for entry in sorted_deliveries if entry["distance"]<= 2000]  #skip for < 2000 Meter for now

			if not result:
				frappe.local.response['http_status_code'] = 400

				
			return result
		else:
			frappe.local.response['http_status_code'] = 400
			frappe.local.response['message'] = _(f"""Their are no store assign to this user: {frappe.session.user}""")
	except Exception as e:
		frappe.log_error(message=str(e), title=_('Error in search_delivary'))
		frappe.local.response['http_status_code'] = 400
		return {
			"status_code": 500,
			"message": str(e)
		}


@frappe.whitelist()
def create_request_for_delivery(delivary , name_request):
	doc = frappe.new_doc("Request")
	doc.delivery = delivary
	doc.request = name_request
	doc.save()
	frappe.db.commit()
	return doc.name


@frappe.whitelist(allow_guest=False)
def res_for_delivary(req_del_name , status):
	doc = frappe.get_doc("Request" , req_del_name)
	doc.status = status
	doc.save()
	return doc

	


@frappe.whitelist(allow_guest=0)
def osm_v1(start_point, end_point):
	start1 = start_point[0]
	start2 = start_point[1]

	end1 = end_point[0]
	end2 = end_point[1]
	url = f"""https://routing.openstreetmap.de/routed-car/route/v1/driving/{start1},{start2};{end1},{end2}?alternatives=false&overview=full&steps=true"""
	response = requests.get(url)
	return response
	route_info = response.json()
	return route_info
	

import frappe
import requests

@frappe.whitelist(allow_guest=1)
def calculate_distance_and_duration(start, end):
	"""
	Calculate distance and duration between start and end coordinates using OpenRouteService.
	
	Args:
		start (str): Start coordinates in "longitude,latitude" format.
		end (str): End coordinates in "longitude,latitude" format.
	
	Returns:
		dict: Distance and duration data from the response.
	"""
	try:
		# Get API details from "Light Integration" doctype
		light_integration = frappe.get_doc("Light Integration")
		api_key = light_integration.api_key
		url = f"{light_integration.api_url}/v2/directions/driving-car"

		# Construct the complete request URL with parameters
		request_url = f"{url}?api_key={api_key}&start={start}&end={end}"

		# Send GET request to the OpenRouteService API
		response = requests.get(request_url)
		return response

		# Check if response is successful
		if response.status_code == 200:
			return response.json()  # Parse JSON and return
		else:
			frappe.log_error(f"Error in OpenRouteService API: {response.status_code} - {response.text}")
			return {"error": "Failed to get data from OpenRouteService."}

	except Exception as e:
		frappe.log_error(f"Exception in calculate_distance_and_duration: {str(e)}")
		return {"error": "An exception occurred while processing the request."}


# @frappe.whitelist(allow_guest=1)
# def calculate_distance_and_duration(start , end ):

# 	"""
# 	https://api.openrouteservice.org/v2/directions/driving-car?api_key=5b3ce3597851110001cf6248e919248db9ed498bbca7120ad13698fc&start=31.0559739,29.907215&end=31.3456224,30.0589113
	
# 	"""
# 	coordinates = [start,end]
# 	light_integration = frappe.get_doc("Light Integration")
# 	url = light_integration.api_url
# 	api_key = light_integration.api_key
# 	headers = {
# 			 'Authorization': api_key,
# 			 'Content-Type': 'application/json; charset=utf-8'
# 		}
# 	data = {
# 			"api_key":api_key,
# 			"start": start,
# 			"end":end
# 		}
# 	response = requests.get(url, params=data, headers=headers)
# 	return response
# 	route_info = response.json()
# 	return route_info
# 	distance = route_info['routes'][0]['summary']['distance']
# 	duration = route_info['routes'][0]['summary']['duration']
# 	res = {
# 		"distance":distance,
# 		"duration":duration
# 		}
# 	return res
	

def haversine(coord1, coord2):
	
	lat1, lon1 = map(math.radians, coord1)
	lat2, lon2 = map(math.radians, coord2)

	dlat = lat2 - lat1
	dlon = lon2 - lon1
	a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
	c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
	r = 6371  
	return r * c


def get_url():
	base_url = frappe.utils.get_url()
	site_config = frappe.get_site_config()
	domains = site_config.get("domains", [])

	url = ""

	if isinstance(domains, list) and domains:

		domain_info = domains[0]
		url = domain_info.get("domain") if isinstance(domain_info, dict) else None
	else:

		port = site_config.get('nginx_port', 8002)  
		url = f"{base_url}:{port}"

	return url


@frappe.whitelist(allow_guest=0)
def upload_images(*args , **kwargs):
	files = frappe.request.files
	data = frappe.form_dict
	try:
		if frappe.db.exists("Order",data.get('order')):
			order = frappe.get_doc("Order" , data.get('order'))
			images = len(order.get("order_image"))
			new_images = len(files)
			if images + new_images > 4:
				order.order_image = []
			if files.get("first_image"):
				first_image = download_image(files.get("first_image"))
				order.append("order_image",{
					"image":first_image.file_url
				})
			if files.get("secound_image"):
				secound_image = download_image(files.get("secound_image"))
				order.append("order_image",{
					"image":secound_image.file_url
				})
			if files.get("third_image"):
				third_image = download_image(files.get("third_image"))
				order.append("order_image",{
					"image":third_image.file_url
				})
			if files.get("forth_image"):
				forth_image = download_image(files.get("forth_image"))
				order.append("order_image",{
					"image":forth_image.file_url
				})
			order.save()
			frappe.db.commit()
			frappe.local.response['http_status_code'] = 200
			frappe.local.response['message'] = _(f"""The Images Updated in {data.get('order')}""")
			
			
		else:
			frappe.local.response['http_status_code'] = 400
			frappe.local.response['message'] = _(f"""Their are no order like this {data.get('order')}""")

	except Exception as e:
		frappe.log_error(message=str(e), title=_('Error in upload_images'))
		return {
			"status_code": 500,
			"message": str(e)
		}





@frappe.whitelist(allow_guest=True)
def download_image(image):

	filename = image.filename

	site_path = frappe.get_site_path('public', 'files')
	file_path = os.path.join(site_path, filename)

	with open(file_path, 'wb') as f:
		f.write(image.read())

	with open(file_path, 'rb') as image_file:
		encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
	new_file = frappe.get_doc({
		"doctype": "File",
		"file_name": filename,
		"is_private": 0,
		"filedata": encoded_string,
		"file_url": f"/files/{filename}"
	})
	new_file.insert(ignore_permissions=True)
	frappe.db.commit()
	return new_file


@frappe.whitelist(allow_guest=True)
def get_store_state(user=None):
	if not user:
		user = "administrator"
	try:
		roles = frappe.get_roles(user)
		if 'Accounts User' in roles:
			
			"""
			Pending
			Active
			Inactive
			"""

			pending = frappe.db.count('Store', {'status': 'Pending'})
			active = frappe.db.count('Store', {'status': 'Active'})
			inactive = frappe.db.count('Store', {'status': 'Inactive'})
			all_stores = frappe.db.count('Store')


			frappe.local.response['http_status_code'] = 200
			return {
				'status_code': 200,
				'message': _('Count of order status'),
				'data': {
					'pending': pending,
					'active': active,
					'inactive': inactive,
					'all_stores': all_stores
				}
			}
		else:
			frappe.local.response['http_status_code'] = 403
			return {
				'status_code': 403,
				'message': _('User does not have the required role'),
				'data': []
			}
	except Exception as e:
		frappe.log_error(message=str(e), title=_('Error in get_store_state'))
		return {
			"status_code": 500,
			"message": str(e)
		}
	


@frappe.whitelist()
def send_notification(UsersArray , content ):

	if content == "modification":
		payload = {
			"app_id": "e75df22c-56df-4e69-8a73-fc80c73c4337",
			"headings": { 
				"en": "Edit Request"
			},
			"title": { 
				"en": "Edit Request"
			},
			"contents": { 
				"en": "You have a modification of request"
			},
			"data": { "postID": "req" },
			"include_player_ids": [UsersArray]
		}
	elif content == "new request":
		payload = {
			"app_id": "e75df22c-56df-4e69-8a73-fc80c73c4337",
			"headings": { 
				"en": "New Request"
			},
			"title": { 
				"en": "New Request Available"
			},
			"contents": { 
				"en": "You have a new request"
			},
			"data": { "postID": "popup_req" },
			"include_player_ids": [UsersArray]
		}
	url = "https://onesignal.com/api/v1/notifications"

	headers = {
		"Content-Type": "application/json; charset=utf-8",
		"Authorization": "Basic NmMwNGNmM2MtYzM5Zi00ODYwLTk0ODYtYWNiMDlkY2M2NDFi"
	}

	

	payload_json = json.dumps(payload)

	response = requests.post(url, headers=headers, data=payload_json)
	return response



def create_error_log(method, error):
	error_log = frappe.new_doc("Error Log")
	error_log.method = method
	error_log.error = error
	error_log.save(ignore_permissions=True)
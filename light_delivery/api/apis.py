import frappe
from frappe import _
import os
import base64
import math
import requests
import json

#from light_delivery.api.apis import

@frappe.whitelist(allow_guest = False)
def search_delivary(cash , user = None ):
	# if not user:
	try:
		user = frappe.session.user
		if frappe.db.exists("Store",{'user':user}):
			store = frappe.get_doc("Store" , {"user":user})
			store_location = json.loads(store.store_location)
			store_coord = store_location.get("features")[0].get("geometry").get("coordinates")

			deliveries = frappe.db.sql(f"""
									select 
										name, pointer_x , pointer_y 
									from 
										`tabDelivery` 
									where 
										status = 'Avaliable' and cash >= {cash} """, as_dict=1)
			distance = []
			
			for delivery in deliveries:
				if delivery['pointer_x'] is not None and delivery['pointer_y'] is not None:
					del_coord = [float(delivery['pointer_x']), float(delivery['pointer_y'])]
					
					temp = calculate_distance_and_duration(del_coord = del_coord, store_coord = store_coord)
					temp['user'] = delivery.get('name')
					temp['coordination'] = del_coord
					distance.append(temp)
			message = sorted(distance,key=lambda x: x['distance'])
			return message
		else:
			frappe.local.response['http_status_code'] = 400
			frappe.local.response['message'] = _(f"""Their are no store assign to this user: {user}""")
	except Exception as e:
		frappe.log_error(message=str(e), title=_('Error in search_delivary'))
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

	




def calculate_distance_and_duration(del_coord , store_coord ):
	coordinates = [del_coord,store_coord]
	light_integration = frappe.get_doc("Light Integration")
	url = light_integration.api_url
	api_key = light_integration.api_key
	headers = {
    	     'Authorization': api_key,
    	     'Content-Type': 'application/json; charset=utf-8'
    	}
	data = {
    	     "coordinates": coordinates
    	}
	response = requests.post(url, json=data, headers=headers)
	route_info = response.json()
	distance = route_info['routes'][0]['summary']['distance']
	duration = route_info['routes'][0]['summary']['duration']
	res = {
		"distance":distance,
		"duration":duration
		}
	return res
	

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
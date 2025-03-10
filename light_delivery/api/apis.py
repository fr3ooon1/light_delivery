import frappe
from frappe import _
import os
import base64
import math
import requests
import json
# from light_delivery.api.delivery_request import get_balance

COMPANY = frappe.defaults.get_defaults().get("company")
Deductions = "Deductions"



@frappe.whitelist()
def send_sms(mobiles , order):
	setting = frappe.get_doc("Deductions")

	doc = frappe.get_doc("Order",order)
	# message = f"{setting.message}"

	message = f"""
		Hello '{doc.full_name}',
		Your order no. '{doc.name}' successfully created
	"""

	url = f"{setting.url}?username={setting.username}&password={setting.password}&sendername={setting.sendername}&message={message}&mobiles={mobiles}"

	payload = {}
	headers = {}

	response = requests.request("GET", url, headers=headers, data=payload)

	print(response.text)


@frappe.whitelist()
def make_journal_entry(kwargs):
	try:
		# Create the Journal Entry document
		doc = frappe.get_doc({
			"doctype": "Journal Entry",
			"voucher_type": "Journal Entry",
			"naming_series": "ACC-JV-.YYYY.-",
			"company": COMPANY,
			"cheque_no": kwargs.get("order"),
			"cheque_date": frappe.utils.now_datetime(),
			"posting_date": frappe.utils.now_datetime(),
		})

		# Append the debit entry
		
		doc.append("accounts", {
			"account": kwargs.get("account_debit"),
			"party_type":kwargs.get("party_type_debit"),
			"party":kwargs.get("party_debit"),
			"debit_in_account_currency": kwargs.get("amount_debit", 0),
			"credit_in_account_currency": 0,
		})

		# Append the credit entry
		doc.append("accounts", {
			"account": kwargs.get("account_credit"),
			"party_type":kwargs.get("party_type_credit"),
			"party":kwargs.get("party_credit"),
			"debit_in_account_currency": 0,
			"credit_in_account_currency": kwargs.get("amount_credit", 0),
		})
		doc.docstatus = 1
		doc.insert(ignore_permissions=True)
		frappe.db.commit()

		return doc.name

	except Exception as e:
		frappe.log_error(message=str(e), title=_('Error in make_journal_entry'))
		frappe.throw(_("An error occurred while creating the Journal Entry: {0}").format(str(e)))
	

@frappe.whitelist()
def check_ledger(kwargs):
	doc = {
			"doctype": "Journal Entry",
			"voucher_type": "Journal Entry",
			"naming_series": "ACC-JV-.YYYY.-",
			"company": COMPANY,
			"cheque_no": kwargs.get("order"),
			"accounts": [
				{
					"account": kwargs.get("account_debit"),
					"party_type": kwargs.get("party_type_debit"),
					"party": kwargs.get("party_debit"),
					"debit_in_account_currency": kwargs.get("amount_debit", 0),
					"credit_in_account_currency": 0,
				},
				{
					"account": kwargs.get("account_credit"),
					"party_type": kwargs.get("party_type_credit"),
					"party": kwargs.get("party_credit"),
					"debit_in_account_currency": 0,
					"credit_in_account_currency": kwargs.get("amount_credit", 0),
				},
			]
		}

	print(doc)

	existing_entry = frappe.get_doc(doc)
	if existing_entry:
		return True
	else:
		return False
	
@frappe.whitelist()
def get_balance(party):
	balance = 0
	sql = f"""
			SELECT 
				SUM(jea.credit_in_account_currency) - SUM(jea.debit_in_account_currency) AS total
			FROM
				`tabJournal Entry Account` as jea
			JOIN 
				`tabJournal Entry` AS je ON je.name = jea.parent
			WHERE
				jea.party = '{party}'
				AND je.docstatus = 1
				;

	"""
	sql = frappe.db.sql(sql,as_dict=1)
	if sql:
		balance = float(sql[0].get("total") or 0)
	return balance


@frappe.whitelist(allow_guest=False)
def search_delivary(cash, store=None, order_type=None):
    try:
        cash = float(cash or 0)

        # Get the store assigned to the current user if not provided
        if not store:
            store = frappe.get_value("Store", {"user": frappe.session.user}, "name")

        if frappe.db.exists("Store", store):
            try:
                store_doc = frappe.get_value("Store", store, ["pointer_x", "pointer_y"], as_dict=1)
                store_coord = [float(store_doc.get("pointer_x") or 0), float(store_doc.get("pointer_y") or 0)]
            except (KeyError, ValueError, IndexError):
                frappe.throw(_("Invalid store location format for Store: {0}").format(store))

            # Adjust condition based on order_type
            if order_type == "Refund":
                cash_condition = f" AND d.cash >= {cash}"
            else:
                cash_condition = f"""
                AND (d.cash + COALESCE(
                    (SELECT 
                        SUM(jea.credit_in_account_currency) - SUM(jea.debit_in_account_currency)
                    FROM 
                        `tabJournal Entry Account` AS jea
                    WHERE 
                        jea.party = d.delivery_name), 0)) >= {cash}
                """

            # Fetch deliveries
            deliveries = frappe.db.sql(f"""
            SELECT 
                d.name AS name, 
                d.user AS user, 
                d.pointer_x AS pointer_x, 
                d.pointer_y AS pointer_y, 
                u.notification_key AS notification_key, 
                d.cash AS cash
            FROM 
                `tabDelivery` d
            JOIN 
                `tabUser` u ON d.user = u.name
            WHERE 
                d.status = 'Avaliable' 
                {cash_condition}
            """, as_dict=True)

            # Calculate distances and filter deliveries
            distance = []
            searching_area = frappe.db.get_single_value('Deductions', 'searching_area')
            for delivery in deliveries:
                if delivery['pointer_x'] is not None and delivery['pointer_y'] is not None:
                    del_coord = [float(delivery['pointer_x']), float(delivery['pointer_y'])]
                    dist = float(haversine(coord1=del_coord, coord2=store_coord) or 0) * 1000  # Convert to meters
                    if dist <= float(searching_area or 0):  
                        distance.append({
                            'distance': dist,
                            'user': delivery.get('user'),
                            'name': delivery.get('name'),
                            'coordination': del_coord,
                            'notification_key': delivery.get("notification_key"),
                        })

            sorted_deliveries = sorted(distance, key=lambda x: x['distance'], reverse=True)

            if not sorted_deliveries:
                frappe.local.response['http_status_code'] = 400
                return []

            return sorted_deliveries

        else:
            frappe.local.response['http_status_code'] = 400
            return {
                "message": _("There is no store assigned to this user: {0}").format(frappe.session.user)
            }

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

import hmac
import hashlib
import requests

@frappe.whitelist()
def sms(reciever):
	# Parameters
	secret_key = "644D22EBED7B44D181B51EEBB8C80D2D"
	url = "https://e3len.vodafone.com.eg/web2sms/sms/submit/"

	msg = "Hello"
	account_id = "550163042"
	password = "Vodafone.1"
	sender_name = "Light&amp;Fast" 

	# data = f"""{account_id}{password}{sender_name}{reciever}{msg}"""

	data = f"""AccountId={account_id}&Password={password}&SenderName={sender_name}&ReceiverMSISDN={reciever}&SMSText={msg}"""
	print(data)

	
	secure_hash = hmac.new(secret_key.encode(), data.encode(), hashlib.sha256).hexdigest()

	secure_hash =  secure_hash.encode('utf-8')

	print(secure_hash)

	payload = f"""
	<?xml version="1.0" encoding="UTF-8"?>
	<SubmitSMSRequest xmlns="http://www.edafa.com/web2sms/sms/model/">
	<AccountId>{account_id}</AccountId>
	<Password>{password}</Password>
	<SecureHash>{secure_hash}</SecureHash>
	<SMSList>        
		<SenderName>{sender_name}</SenderName>      
		<ReceiverMSISDN>{reciever}</ReceiverMSISDN>        
		<SMSText>{msg}</SMSText>
	</SMSList>
	</SubmitSMSRequest>"""
	
	headers = {
		'Content-Type': 'application/xml'
	}

	try:
		response = requests.request("POST", url, headers=headers, data=payload)
		print(response.text)
		# frappe.log_error(f"Vodafone SMS Response: {response.text}", "SMS API Debug")
		return {"status_code": response.status_code, "response": response.text}
	except Exception as e:
		# frappe.log_error(f"Error: {str(e)}", "SMS API Debug")
		print(e)	
		return {"error": str(e)}



# @frappe.whitelist()
# def send_sms(reciever):

# 	secret_key = "644D22EBED7B44D181B51EEBB8C80D2D"
# 	url = "https://e3len.vodafone.com.eg/web2sms/sms/submit/"

# 	msg = "Hello"
# 	account_id = "550163042"
# 	password = "Vodafone.1"
# 	sender_name = "Light&amp;Fast" 

# 	data = f"""AccountId={account_id}&Password={password}&SenderName={sender_name}&ReceiverMSISDN={reciever}&SMSText={msg}"""

# 	secure_hash = hmac.new(secret_key.encode(), data.encode(), hashlib.sha256).hexdigest()

# 	secure_hash =  secure_hash.encode('utf-8')


# 	url = "https://e3len.vodafone.com.eg/web2sms/sms/submit/"

# 	payload = f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?> <SubmitSMSRequest xmlns:=\"http://www.edafa.com/web2sms/sms/model/\"\n
# 	xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xsi:schemaLocation=\"http://www.edafa.com/web2sms/sms/model/\nSMSAPI.xsd \" xsi:type=\"SubmitSMSRequest\">    \n
# 	<AccountId>{account_id}</AccountId>\n    
# 	<Password>{password}</Password>\n    
# 	<SecureHash>{secure_hash}</SecureHash>\n
# 	<SMSList>\n        
# 		<SenderName>{sender_name}</SenderName>\n        
# 		<ReceiverMSISDN>{reciever}</ReceiverMSISDN>\n        
# 		<SMSText>{msg}</SMSText>\n    
# 		</SMSList>\n
# 	</SubmitSMSRequest>"""	
# 	headers = {
# 	'Content-Type': 'application/xml'
# 	}

# 	response = requests.request("POST", url, headers=headers, data=payload)

# 	return response



@frappe.whitelist(allow_guest=0)
def search_by_zone(coord1):
	"""
	Search for zones where the given coordinate is within their radius.

	Args:
		coord1 (list): A list with latitude and longitude of the input point [lat, lon].
	
	Returns:
		list: A list of zone IDs where the input coordinate falls within the radius.
	"""
	# Validate input
	if not coord1 or len(coord1) != 2:
		frappe.throw("Invalid input. Coordinate must be a list with two elements: [latitude, longitude].")
	
	try:
		# Convert coord1 to float values
		coord1 = [float(coord1[0]), float(coord1[1])]
	except ValueError:
		frappe.throw("Coordinates must be valid float values.")

	result = []
	zones = frappe.get_all("Zone Address", fields=["name as id", "geolocation_klnh"])
	
	for zone in zones:
		geolocation_klnh = json.loads(zone.get("geolocation_klnh") or "{}")

		# print(geolocation_klnh)
		# return geolocation_klnh
		
		# Extract geometry and radius information
		features = geolocation_klnh.get("features", [])
		if not features or len(features) == 0:
			continue  # Skip if no features are found
		
		geometry = features[0].get("geometry", {})
		properties = features[0].get("properties", {})
		
		# Validate geometry and properties
		coord2 = geometry.get("coordinates")
		radius = properties.get("radius")
		if not coord2 or not radius:
			continue  # Skip invalid zone data
		
		# Calculate distance
		distance = haversine(coord1, coord2)
		
		print(f"Zone: {zone.get('id')}, Radius: {radius}, Distance: {distance}")

		# return f"Zone: {zone.get('id')}, Radius: {radius}, Distance: {distance}"
		
		# Check if the coordinate is within the zone's radius
		if distance <= (radius):  # Convert radius from meters to kilometers
			result.append(zone.get("id"))
	
	return result

	


@frappe.whitelist(allow_guest=0)
def osm_v1(start_point, end_point):
	start1 = start_point[0]
	start2 = start_point[1]

	end1 = end_point[0]
	end2 = end_point[1]
	url = f"""https://routing.openstreetmap.de/routed-car/route/v1/driving/{start1},{start2};{end1},{end2}?alternatives=false&overview=full&steps=true"""
	response = requests.get(url)
	return response
	

@frappe.whitelist(allow_guest=1)
def osm_v2(start, end):
	"""
	Calculate distance and duration between start and end coordinates using OpenRouteService.
	
	Args:
		start (str): Start coordinates in "longitude,latitude" format.
		end (str): End coordinates in "longitude,latitude" format.
	
	Returns:
		dict: Distance and duration data from the response.
	"""
	try:

		light_integration = frappe.get_doc("Light Integration")
		api_key = light_integration.api_key
		api_url = light_integration.api_url

		request_url = f"{api_url}?api_key={api_key}&start={start}&end={end}"

		response = requests.get(request_url)

		return response

	except Exception as e:
		frappe.log_error(f"Exception in osm_v2: {str(e)}")
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
		url = f"{base_url}"

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
			order.save(ignore_permissions=True)
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
def version(**kwargs):
	last_version = "1.0.1"
	version = kwargs.get("version")

	if version == last_version:
		return True
	else:
		return False

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
			# "priority": 8,
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
			"include_player_ids": [UsersArray],
		}
	elif content == "new request":
		payload = {
			"app_id": "e75df22c-56df-4e69-8a73-fc80c73c4337",
			# "priority": 8,
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
			"include_player_ids": [UsersArray],
			"target_channel": "push",
			"android_sound": "onesignal_default_sound.wav",
			"android_channel_id": "0c37b127-303f-45a4-b298-b8af0f81c9f0",
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
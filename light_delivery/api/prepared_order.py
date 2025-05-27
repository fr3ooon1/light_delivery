import frappe
from frappe import _
from light_delivery.api.apis import download_image


@frappe.whitelist(allow_guest=False)
def prepared_order(*args, **kwargs):

	if frappe.request.method == 'GET':
		return get_order()
	if frappe.request.method == 'POST':
		return post_order()
	if frappe.request.method == 'PUT':
		return update_order()
	if frappe.request.method == 'DELETE':
		return delete_order()


def delete_order():
	try:
		data = frappe.form_dict
		id = data.get("order_id")
		if id:
			if not frappe.db.exists("Prepared Order", id):
				frappe.local.response['http_status_code'] = 400
				frappe.response["message"] = _("Order ID is not valid")
				return
			if frappe.db.get_value("Prepared Order", id, "done") == 1:
				frappe.local.response['http_status_code'] = 400
				frappe.response["message"] = _("Order ID is already submitted can't be deleted")
				return
			# return id
			frappe.delete_doc("Prepared Order", id)
			frappe.local.response['http_status_code'] = 200
			frappe.response["message"] = _("Prepared Order Deleted")
		else:
			frappe.local.response['http_status_code'] = 400
			frappe.response["message"] = _("Order ID is required")
	except Exception as er:
		frappe.log_error("error in prepared order", str(er))
		frappe.local.response['http_status_code'] = 400
		frappe.response["message"] = _(f"{er}")

def update_order():
	try:
		data = frappe.form_dict
		id = data.get("order_id")
		type = data.get("type")
		if type == "edit":
			data = data.get("order")
			order = frappe.get_doc("Prepared Order", id)
			if order:
				order.note = data.get("note") if data.get("note") else order.note
				order.total = data.get("total") if data.get("total") else order.total
				order.address = data.get("address") if data.get("address") else order.address
				order.save(ignore_permissions=True)
				frappe.db.commit()
				frappe.local.response['http_status_code'] = 200
				frappe.response["message"] = _("Prepared Order Updated")

		elif type == "submit":
			data = data.get("order")
			order = frappe.get_doc("Prepared Order", id)
			if order.done == 1:
				frappe.local.response['http_status_code'] = 400
				frappe.response["message"] = _("Order ID is already submitted")
				return
			
			if order:
				order.done = 1
				order.note = data.get("note") if data.get("note") else order.note
				order.total = data.get("total") if data.get("total") else order.total
				order.address = data.get("address") if data.get("address") else order.address
				

				doc = frappe.new_doc("Order")
				doc.full_name = order.full_name
				doc.order_type = order.order_type
				doc.note = order.note
				doc.address = order.address
				doc.order_date = order.order_date
				doc.status = "Pending"
				doc.phone_number = order.phone_number
				doc.total_order = order.total
				if order.get("order_image"):
					for i in order.get("order_image"):
						doc.append("order_image", {
							"image": i.image
						})
				doc.store = order.store
				doc.save(ignore_permissions=True)


				order.order = doc.name
				order.save(ignore_permissions=True)
				

				frappe.db.commit()
				frappe.local.response['http_status_code'] = 200
				frappe.response["message"] = _("Prepared Order Submitted")
		return 
	except Exception as er:
		frappe.log_error("error in prepared order", str(er))
		frappe.local.response['http_status_code'] = 400
		frappe.response["message"] = _(f"{er}")

def get_order():
	try:
		user = frappe.session.user
		user = frappe.get_value("User", user ,["username","full_name" , "mobile_no"],as_dict=True)
		customer = frappe.get_value("Customer",user.get("username"),'name')
		if customer:
			filters = {"phone_number":user.get("mobile_no")}
		store = frappe.get_value("Store",{"user":frappe.session.user},'name')
		if store:
			filters = {"store":store}
		
		args = frappe.request.args
		if args :
			filters["name"] = args.get("name")
		
		filters["done"] = 0
		
		doc = frappe.get_list("Prepared Order", filters=filters , fields=["name","full_name","mobile_no","order_type","note","order_date","phone_number","store","total"], order_by="creation desc")
		if doc:
			for i in doc:
				images = frappe.get_all("Order Image", filters={"parent":i.get("name")}, fields=["image"])
				if images:
					i["order_image"] = frappe.get_list("Order Image", filters={"parent":i.get("name")}, fields=["image"] , pluck="image",ignore_permissions=True)

				else:
					i["order_image"] = []
			frappe.local.response['http_status_code'] = 200
			frappe.response["data"] = doc
		else:
			frappe.local.response['http_status_code'] = 400
			frappe.response["message"] = _("No Orders Found")
	except Exception as er:
		frappe.log_error("error in prepared order", str(er))
		frappe.local.response['http_status_code'] = 400
		frappe.response["message"] = _(f"{er}")



def post_order():
	try:
		user = frappe.session.user
		user = frappe.get_value("User", user ,["username","full_name" , "mobile_no"],as_dict=True)
		customer = frappe.get_value("Customer",user.get("username"),'name')

		files = frappe.request.files
		data = frappe.form_dict

		note = data.get("note")
		store = data.get("store")
		address = data.get("address")

		doc = frappe.new_doc("Prepared Order")
		doc.full_name = user.get("full_name")
		doc.mobile_no = user.get("mobile_no")
		doc.order_type = "Delivery"
		doc.note = note
		doc.order_date = frappe.utils.now()
		doc.phone_number = user.get("mobile_no")
		doc.store = store
		doc.address = address

		if files:
			for i in files.getlist('order_image'):
				saved_file = download_image(i)
				if saved_file:
					doc.append("order_image", {
						"image": saved_file.file_url 
					})

		doc.save(ignore_permissions=True)
		frappe.db.commit()
		frappe.local.response['http_status_code'] = 200
		frappe.response["message"] = _("Prepared Order Created")
	except Exception as er:
		frappe.log_error("error in prepared order", str(er))
		frappe.local.response['http_status_code'] = 400
		frappe.response["message"] = _(f"{er}")


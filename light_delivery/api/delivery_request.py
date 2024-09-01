import frappe

@frappe.whitelist(allow_guest = 0 )
def get_delivery_request():
	store = frappe.db.sql(f"select name from `tabStore` where user = '{frappe.session.user}' " , as_dict = 1)
	sql = f'''
	        select 
	            r.name , r.delivery ,
                GROUP_CONCAT(o.order ORDER BY o.order SEPARATOR ',') AS orders
			from 
			    `tabRequest Delivery` r
			inner join
                `tabOrder Request` o
			    on 
                r.name = o.parent
			where 
			    r.store = '{store[0]["name"]}'
			group by 
                r.name , r.delivery
			'''
	requests = frappe.db.sql(sql , as_dict = 1)
	if requests :
		for request in requests :
			request['orders'] = request['orders'].split(',')
			delivery_pointers = frappe.db.sql(f'''select pointer_x , pointer_y from `tabDelivery` where name = '{request["delivery"]}' ''', as_dict = 1)
			request["pointer_x"] = delivery_pointers[0]["pointer_x"]
			request["pointer_y"] = delivery_pointers[0]["pointer_y"]
		
	return requests

@frappe.whitelist(allow_guest = 0 )
def delivery_cancel_request(id):
	return frappe.session.user
	delivery = frappe.db.sql( f'''select delivery from `tabRequest Delivery` where name = '{id}'  ''' ,as_dict =1 )
	minimum_rate = frappe.db.sql( 
		f'''select  
		        c.minimum_rate
			from 
			    `tabDelivery Category` c
			inner join 
			    `tabDelivery` d 
			on 
			    d.delivery_category = c.name
			where 
			    d.name = '{delivery[0]["delivery"]}'  '''   , as_dict = 1)
	return minimum_rate
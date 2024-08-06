import frappe

@frappe.whitelist(allow_guest = 1)
def get_category():
    categories = frappe.get_list("Store Category" , fields = ['name' , 'category_name_in_arabic'])
    return categories

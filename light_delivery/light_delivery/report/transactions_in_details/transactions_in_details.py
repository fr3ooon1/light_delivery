# Copyright (c) 2024, Muhammad Essam and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    # Retrieve the filtered transactions based on the party type and name
    transactions = get_filtered_transactions(filters)
    
    # Determine the dynamic options based on the party type filter
    party_type_filter = filters.get("party_type")

    dynamic_options = ""
    if party_type_filter == "Delivery": 
        dynamic_options = "Delivery"
    elif party_type_filter == "Store": 
        dynamic_options = "Store"
        
    columns = [
        {
            "label": _("Name"),
            "fieldname": "name",
            "fieldtype": "Dynamic Link",
            "options": "party",
            "width": 300
        },
        {
            "label": _("Debit"),
            "fieldname": "debit",
            "fieldtype": "Currency",
            "width": 200
        },
        {
            "label": _("Credit"),
            "fieldname": "credit",
            "fieldtype": "Currency",
            "width": 200
        },
		{
            "label": _("Against"),
            "fieldname": "against",
            "fieldtype": "Dynamic Link",
            "options": "party",
            "width": 300
        },
		{
            "label": _("Net Balance"),
            "fieldname": "net_balance",
            "fieldtype": "Currency",
            "width": 200
        },
    ]
    
    return columns, transactions

def get_filtered_transactions(filters):
    party_type_filter = filters.get("party_type")
    party_name_filter = filters.get("party")

    filters = {
        "party_type": party_type_filter,
        "party": party_name_filter
    }

    transactions = frappe.get_all("Transactions", 
                                  fields=["party_type", "party", "against", "against_from", "in_wallet", "out"],
                                  filters=filters)

    result = []
	
    for transaction in transactions:
        party_name = transaction.get("party_type")
        debit = transaction.get("in_wallet")
        credit = transaction.get("out")
        against = transaction.get("against_from")
        net_balance = debit - credit

        result.append({
			"against": against,
            "name": party_name,
            "debit": debit,
            "credit": credit,
            "net_balance": net_balance
        })

    return result


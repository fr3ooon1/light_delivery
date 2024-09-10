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
            "width": 200
        },
        {
            "label": _("Debit"),
            "fieldname": "debit",
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "label": _("Credit"),
            "fieldname": "credit",
            "fieldtype": "Currency",
            "width": 150
        },
		{
            "label": _("Against"),
            "fieldname": "against",
            "fieldtype": "Dynamic Link",
            "options": "party",
            "width": 200
        },
		{
            "label": _("Net Balance"),
            "fieldname": "net_balance",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Is Paid"),
            "fieldname": "paid",
            "fieldtype": "Check",
            "width": 100
        },
        {
            "label": _("Voucher"),
            "fieldname": "voucher",
            "fieldtype": "Select",
            "options": "Get Order\nPay Order\nPay Planty",
            "width": 150
        },
        {
            "label": _("Reference"),
            "fieldname": "reference",
            "fieldtype": "Link",
            "options": "Closing operations",
            "width": 150
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
                                  fields=["party_type", "party", "against", "against_from", "in_wallet", "out", "balance", "voucher", "reference", "paid"],
                                  filters=filters)

    result = []
	
    for transaction in transactions:
        party_name = transaction.get("party_type")
        debit = transaction.get("in_wallet")
        credit = transaction.get("out")
        against = transaction.get("against_from")
        net_balance = transaction.get("balance")
        ref = transaction.get("reference")
        voucher = transaction.get("voucher")
        paid = transaction.get("paid")

        result.append({
			"against": against,
            "name": party_name,
            "debit": debit,
            "credit": credit,
            "net_balance": net_balance,
            "reference": ref,
            "voucher": voucher,
            "paid": paid
        })

    return result


# Copyright (c) 2024, Muhammad Essam and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    
    store_balances = get_store_balances(filters)
    party_type_filter = filters.get("party")

    dynamicOptions =""
    if party_type_filter == "Delivery": 
        dynamicOptions = "Delivery"; 
    if party_type_filter == "Store": 
        dynamicOptions = "Store"; 
        
    columns = [
        {
            "label": _("Name"),
            "fieldname": "name",
            "fieldtype": "Link",
            "options": dynamicOptions,
            "width": 300
        },
        {
            "label": _("Debit Balance"),
            "fieldname": "debit_balance",
            "fieldtype": "Currency",
            "width": 200
        },
        {
            "label": _("Credit Balance"),
            "fieldname": "credit_balance",
            "fieldtype": "Currency",
            "width": 200
        },
        {
            "label": _("Net Balance"),
            "fieldname": "net_balance",
            "fieldtype": "Currency",
            "width": 200
        }
    ]
    
    return columns, store_balances

def get_store_balances(filters):
    store_balances = {}

    party_type_filter = filters.get("party")

    transactions = frappe.get_all("Transactions", fields=["party_type", "party", "against", "against_from", "in", "out"])

    for transaction in transactions:
        party_type = transaction.get("party")
        party_name = transaction.get("party_type")
        against_name = transaction.get("against")
        against_from = transaction.get("against_from")
        debit = transaction.get("in", 0)
        credit = transaction.get("out", 0)

        dynamic_name = None

        # Determine whether to use "Store" or "Delivery" based on the filter
        if party_type_filter == "Store":
            if party_type == "Store":
                dynamic_name = party_name
            elif against_name == "Store":
                dynamic_name = against_from
        elif party_type_filter == "Delivery":
            if party_type == "Delivery":
                dynamic_name = party_name
            elif against_name == "Delivery":
                dynamic_name = against_from

        if dynamic_name:
            if dynamic_name not in store_balances:
                store_balances[dynamic_name] = {
                    "debit_balance": 0,
                    "credit_balance": 0,
                    "net_balance": 0
                }

            store_balances[dynamic_name]["debit_balance"] += debit
            store_balances[dynamic_name]["credit_balance"] += credit
            store_balances[dynamic_name]["net_balance"] += debit - credit

    result = []
    for dynamic_name, balances in store_balances.items():
        result.append({
            "name": dynamic_name,  
            "debit_balance": balances["debit_balance"],
            "credit_balance": balances["credit_balance"],
            "net_balance": balances["net_balance"]
        })

    return result


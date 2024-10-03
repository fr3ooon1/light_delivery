from __future__ import unicode_literals
import frappe
from frappe import _

data = {
	'custom_fields': {
            'User':[	
                {
				"label": "Notification Key",
				"fieldname": "notification_key",
				"fieldtype": "Data",
				"insert_after": "api_secret" ,
                "read_only":1
				},
			],
	},
		"properties": [
            		
	],  
}
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
			'Journal Entry':[	
                {
				"label": "Finished Order",
				"fieldname": "finished_order",
				"fieldtype": "Check",
				"insert_after": "multi_currency" ,
                "read_only":1
				},
			],
            'Address':[
                {
				"label": "latitude",
				"fieldname": "latitude",
				"fieldtype": "Data",
				"insert_after": "address_line2" ,
                "read_only":0
				},
                {
				"label": "longitude",
				"fieldname": "longitude",
				"fieldtype": "Data",
				"insert_after": "latitude" ,
                "read_only":0
				},
			]
	},
		"properties": [
            		
	],  
}
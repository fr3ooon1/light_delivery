app_name = "light_delivery"
app_title = "Light Delivery"
app_publisher = "Muhammad Essam"
app_description = "Delivery Mobile App"
app_email = "mohamed.essam68.me@gmail.com"
app_license = "mit"
app_logo_url = "/assets/light_delivery/image/logo.png"
# required_apps = []
website_route_rules = [
    # {"from_route": "/custom_search", "to_route": "api/method/light_delivery.api.order.search_by_phone"},
]
# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/light_delivery/css/light_delivery.css"
# app_include_js = "/assets/light_delivery/js/light_delivery.js"

# include js, css files in header of web template
# web_include_css = "/assets/light_delivery/css/light_delivery.css"
# web_include_js = "/assets/light_delivery/js/light_delivery.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "light_delivery/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "light_delivery/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "light_delivery.utils.jinja_methods",
# 	"filters": "light_delivery.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "light_delivery.install.before_install"
# after_install = "light_delivery.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "light_delivery.uninstall.before_uninstall"
# after_uninstall = "light_delivery.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "light_delivery.utils.before_app_install"
# after_app_install = "light_delivery.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "light_delivery.utils.before_app_uninstall"
# after_app_uninstall = "light_delivery.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "light_delivery.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

scheduler_events = {
    "cron": {
		"* * * * *": [
			"light_delivery.api.delivery_request.sending_request",
		],
	},
	# "all": [
	# 	"light_delivery.tasks.all"
	# ],
	"daily": [
		"light_delivery.light_delivery.doctype.delivery.delivery.update_delivery_category"
	],
	# "hourly": [
	# 	"light_delivery.tasks.hourly"
	# ],
	# "weekly": [
	# 	"light_delivery.tasks.weekly"
	# ],
	# "monthly": [
	# 	"light_delivery.tasks.monthly"
	# ],
}

# Testing
# -------

# before_tests = "light_delivery.install.before_tests"

# Overriding Methods
# ------------------------------
#
domains = {
    "Light Delivery" : "light_delivery.domains.light_delivery",
}



override_whitelisted_methods = {
	"search_by_phone":"light_delivery.api.order.search_by_phone"
}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "light_delivery.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["light_delivery.utils.before_request"]
# after_request = ["light_delivery.utils.after_request"]

# Job Events
# ----------
# before_job = ["light_delivery.utils.before_job"]
# after_job = ["light_delivery.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"light_delivery.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

after_install = [
    "light_delivery.setup.after_install",
    ]

after_migrate = [
    "light_delivery.setup.after_install",
]

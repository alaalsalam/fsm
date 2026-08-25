app_name = "fsm"
app_title = "Field Service Management"
app_publisher = "Kodlyft"
app_description = "A field service management app for frappe"
app_email = "hello@kodlyft.com"
app_license = "mit"

# Apps
# ------------------

required_apps = ["erpnext"]

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "fsm",
# 		"logo": "/assets/fsm/logo.png",
# 		"title": "Field Service Management",
# 		"route": "/fsm",
# 		"has_permission": "fsm.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/fsm/css/fsm.css"
# app_include_js = "/assets/fsm/js/fsm.js"

# include js, css files in header of web template
# web_include_css = "/assets/fsm/css/fsm.css"
# web_include_js = "/assets/fsm/js/fsm.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "fsm/public/scss/website"

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
# app_include_icons = "fsm/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Website routes
# --------------
# Serve the Vue SPAs (built by `yarn build` into fsm/public/{console,portal} and copied to
# fsm/www/{console,book}.html). These rules make client-side deep links resolve to the SPA
# entry page. Console = back office (auth via API); /book = public customer portal.
website_route_rules = [
	{"from_route": "/fsm-console/<path:app_path>", "to_route": "fsm-console"},
	{"from_route": "/book/<path:app_path>", "to_route": "book"},
]

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "fsm.utils.jinja_methods",
# 	"filters": "fsm.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "fsm.install.before_install"
after_install = "fsm.setup.after_install"
after_migrate = "fsm.setup.after_migrate"

# Uninstallation
# ------------

# before_uninstall = "fsm.uninstall.before_uninstall"
# after_uninstall = "fsm.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "fsm.utils.before_app_install"
# after_app_install = "fsm.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "fsm.utils.before_app_uninstall"
# after_app_uninstall = "fsm.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "fsm.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "fsm.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

permission_query_conditions = {
	"Service Job": "fsm.security.permissions.service_job_query",
	"Service Request": "fsm.security.permissions.service_request_query",
	"Service Visit": "fsm.security.permissions.service_visit_query",
	"Service Event Log": "fsm.security.permissions.event_log_query",
	"Customer Site": "fsm.security.permissions.customer_site_query",
	"Equipment Location": "fsm.security.permissions.equipment_location_query",
	"Installed Equipment": "fsm.security.permissions.installed_equipment_query",
	"Service Return": "fsm.security.permissions.service_return_query",
	"Service Job Message": "fsm.security.permissions.message_query",
	"Service Feedback": "fsm.security.permissions.feedback_query",
	"Service Time Log": "fsm.security.permissions.time_log_query",
	"Customer Field Note": "fsm.security.permissions.field_note_query",
	"Technician Location Log": "fsm.security.permissions.location_log_query",
	"Maintenance Plan": "fsm.security.permissions.maintenance_plan_query",
	"Maintenance Occurrence": "fsm.security.permissions.maintenance_occurrence_query",
	"Inspection Template": "fsm.security.permissions.inspection_template_query",
	"Equipment Inspection": "fsm.security.permissions.equipment_inspection_query",
	"Failure Analysis": "fsm.security.permissions.failure_analysis_query",
	"Service Report": "fsm.security.permissions.service_report_query",
	"Service Certificate": "fsm.security.permissions.service_certificate_query",
}

has_permission = {
	"Service Job": "fsm.security.permissions.service_job_permission",
	"Service Request": "fsm.security.permissions.service_request_permission",
	"Service Visit": "fsm.security.permissions.service_visit_permission",
	"Service Event Log": "fsm.security.permissions.event_log_permission",
	"Customer Site": "fsm.security.permissions.customer_site_permission",
	"Equipment Location": "fsm.security.permissions.equipment_location_permission",
	"Installed Equipment": "fsm.security.permissions.installed_equipment_permission",
	"Service Return": "fsm.security.permissions.job_child_permission",
	"Service Job Message": "fsm.security.permissions.job_child_permission",
	"Service Feedback": "fsm.security.permissions.job_child_permission",
	"Service Time Log": "fsm.security.permissions.job_child_permission",
	"Customer Field Note": "fsm.security.permissions.job_child_permission",
	"Technician Location Log": "fsm.security.permissions.job_child_permission",
	"Maintenance Plan": "fsm.security.permissions.maintenance_plan_permission",
	"Maintenance Occurrence": "fsm.security.permissions.maintenance_occurrence_permission",
	"Inspection Template": "fsm.security.permissions.inspection_template_permission",
	"Equipment Inspection": "fsm.security.permissions.equipment_inspection_permission",
	"Failure Analysis": "fsm.security.permissions.job_child_permission",
	"Service Report": "fsm.security.permissions.job_child_permission",
	"Service Certificate": "fsm.security.permissions.job_child_permission",
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Service Job": {
		"on_update": [
			"fsm.realtime.on_service_job_update",
			"fsm.maintenance.projections.on_service_job_update",
		],
	},
	"Technician": {
		"on_update": "fsm.realtime.on_technician_update",
	},
	"Delivery Note": {
		"on_submit": "fsm.installed_base.provisioning.on_delivery_note_submit",
		"on_cancel": "fsm.installed_base.provisioning.on_delivery_note_cancel",
	},
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"hourly": [
		"fsm.tasks.flag_sla_breaches",
	],
	"daily": [
		"fsm.tasks.notify_low_stock",
		"fsm.contracts.tasks.update_contract_statuses",
		"fsm.maintenance.tasks.run_daily_maintenance",
	],
}

# Testing
# -------

# before_tests = "fsm.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "fsm.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "fsm.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "fsm.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["fsm.utils.before_request"]
# after_request = ["fsm.utils.after_request"]

# Job Events
# ----------
# before_job = ["fsm.utils.before_job"]
# after_job = ["fsm.utils.after_job"]

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
# 	"fsm.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

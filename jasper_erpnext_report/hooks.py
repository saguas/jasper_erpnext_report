app_name = "jasper_erpnext_report"
app_title = "Jasper Erpnext Report"
app_publisher = "Luis Fernandes"
app_description = "Make your own reports in jasper and print them in pdf, docx, xlsx and other formats."
app_icon = "icon-file-text"
app_color = "black"
app_email = "luisfmfernandes@gmail.com"
app_url = "http://localhost"
app_version = "0.0.1"



#on_login = "jasper_erpnext_report.core.jaspersession.on_user_login"
#before_install = "jasper_erpnext_report.core.jaspersession.before_install"
before_install = "jasper_erpnext_report.utils.install.before_install"
after_install = "jasper_erpnext_report.utils.install.after_install"
#on_session_creation = "jasper_erpnext_report.core.jaspersession.on_session_creation"
#on_logout = "jasper_erpnext_report.core.jaspersession.on_logout"
boot_session = "jasper_erpnext_report.core.JasperWhitelist.boot_session"
#clear_cache = "jasper_erpnext_report.utils.scheduler.clear_cache"
#write_file = "jasper_erpnext_report.utils.file.write_file_jrxml"
delete_file_data_content = "jasper_erpnext_report.utils.file.delete_file_jrxml"
#website_clear_cache = "jasper_erpnext_report.core.jaspersession.website_clear_cache"
# Includes in <head>
# ------------------

# include js, css files in header of desk.html
#app_include_js = "/assets/jasper_erpnext_report/js/jasper_erpnext_report.js"
app_include_css = ["/assets/jasper_erpnext_report/css/callouts.css"]
#app_include_css = "/assets/css/jasper_erpnext_report.css"
app_include_js = ["/assets/jasper_erpnext_report/js/jstree.min.js", "/assets/jasper_erpnext_report/js/utils.js", "/assets/jasper_erpnext_report/js/jasper_ui.js", "/assets/jasper_erpnext_report/js/upload.js", "/assets/jasper_erpnext_report/js/jasper_erpnext_comm.js", "/assets/jasper_erpnext_report/js/jasper_erpnext_report.js"]
#app_include_js = ["/assets/jasper_erpnext_report/js/meteor.js", "/assets/jasper_erpnext_report/js/jasper_erpnext_report.js"]
#app_include_js = ["/assets/jasper_erpnext_report/js/socket.io.js", "/assets/jasper_erpnext_report/js/meteor.js", "/assets/jasper_erpnext_report/js/jasper_erpnext_report.js"]
#app_include_js = [ "/assets/js/meteor.js" , "/assets/js/jasper_erpnext_report.js"]

# app_include_css = "/assets/jasper_erpnext_report/css/jasper_erpnext_report.css"
# app_include_js = "/assets/jasper_erpnext_report/js/jasper_erpnext_report.js"
# include js, css files in header of web template
# web_include_css = "/assets/jasper_erpnext_report/css/jasper_erpnext_report.css"
# web_include_js = "/assets/jasper_erpnext_report/js/jasper_erpnext_report.js"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "jasper_erpnext_report.install.before_install"
# after_install = "jasper_erpnext_report.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "jasper_erpnext_report.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

permission_query_conditions = {
	"Jasper Reports": "jasper_erpnext_report.jasper_erpnext_report.doctype.jasper_reports.jasper_reports.get_permission_query_conditions",
}
#
has_permission = {
	"Jasper Reports": "jasper_erpnext_report.jasper_erpnext_report.doctype.jasper_reports.jasper_reports.has_jasper_permission",
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Jasper Reports": {
#		"on_update": "jasper_erpnext_report.utils.update_doc.update",
#		"before_save": "jasper_erpnext_report.utils.update_doc.before_save"
#		"on_trash": "method"
		#"on_jasper_params": "jasper_erpnext_report.utils.utils.jasper_params"
	}
}

fixtures = [
	["Custom Field",{"name":["File Data-attached_to_report_name"]}]
]

# Scheduled Tasks
# ---------------
scheduler_events = {
	"daily": [
		"jasper_erpnext_report.utils.scheduler.clear_expired_jasper_sessions"
	],
	"hourly": [
		"jasper_erpnext_report.utils.scheduler.clear_expired_jasper_html"
	]
}
# scheduler_events = {
# 	"all": [
# 		"jasper_erpnext_report.tasks.all"
# 	],
# 	"daily": [
# 		"jasper_erpnext_report.tasks.daily"
# 	],
# 	"hourly": [
# 		"jasper_erpnext_report.tasks.hourly"
# 	],
# 	"weekly": [
# 		"jasper_erpnext_report.tasks.weekly"
# 	]
# 	"monthly": [
# 		"jasper_erpnext_report.tasks.monthly"
# 	]
# }

# Testing
# -------

# before_tests = "jasper_erpnext_report.install.before_tests"

# Overriding Whitelisted Methods
# ------------------------------
#
#override_whitelisted_methods = {
#	"frappe.widgets.reportview.get": "jasper_erpnext_report.utils.reportview.get_list",
#	"frappe.widgets.moduleview.get": "jasper_erpnext_report.utils.moduleview.get_count"
#}


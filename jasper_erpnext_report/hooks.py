app_name = "jasper_erpnext_report"
app_title = "Jasper Erpnext Report"
app_publisher = "Luis Fernandes"
app_description = "Make your own reports in jasper and print them in pdf, docx, xlsx and other formats."
app_icon = "icon-file-text"
app_color = "black"
app_email = "luisfmfernandes@gmail.com"
app_url = "http://localhost"
app_version = "0.1.0"
app_license = "MIT"




before_install = "jasper_erpnext_report.utils.install.before_install"
after_install = "jasper_erpnext_report.utils.install.after_install"

boot_session = "jasper_erpnext_report.core.JasperWhitelist.boot_session"

app_include_css = ["/assets/jasper_erpnext_report/css/style.min.css", "/assets/css/jasper_erpnext_report.css"]

#app_include_js = ["/assets/js/jasper_erpnext_report.js"]

app_include_js = [
 	"/assets/jasper_erpnext_report/js/jstree.min.js",
	"/assets/jasper_erpnext_report/js/utils.js",
	"/assets/jasper_erpnext_report/js/jasper_ui.js",
	"/assets/jasper_erpnext_report/js/upload.js",
	"/assets/jasper_erpnext_report/js/jasper_erpnext_comm.js",
	"/assets/jasper_erpnext_report/js/jasper_erpnext_report.js"

]

permission_query_conditions = {
	"Jasper Reports": "jasper_erpnext_report.jasper_erpnext_report.doctype.jasper_reports.jasper_reports.get_permission_query_conditions",
}

#example custom report fields
#jasper_custom_data_source = {
#	"Cherry Local": "jasper_erpnext_report.jasper_reports.FrappeDataSource.JasperCustomDataSourceDefault"
#}

#permissions

has_permission = {
	"Jasper Reports": "jasper_erpnext_report.jasper_erpnext_report.doctype.jasper_reports.jasper_reports.has_jasper_permission",
}

"""
on_jasper_params = {
	"Cherry Local": "jasper_erpnext_report.utils.utils.testHookReport"
}
"""

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "File":{
		"on_trash": "jasper_erpnext_report.utils.jasper_file_jrxml.delete_file_jrxml",
		"onload": "jasper_erpnext_report.utils.jasper_file_jrxml.onload"
    }
}

fixtures = [
	{"doctype":"Custom Field", "filters": {"fieldname": "attached_to_report_name"}}
]

# Scheduled Tasks
# ---------------
scheduler_events = {
	"daily": [
		"jasper_erpnext_report.utils.scheduler.clear_expired"
	],
}



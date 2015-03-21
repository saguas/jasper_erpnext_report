from __future__ import unicode_literals
__author__ = 'luissaguas'

import frappe, os, jasper_erpnext_report, re
from frappe import _

no_cache = True

def get_context(context):
	#rg = r'<body[^>]*>(.*?)</body>'
	jasper_report_path = frappe.form_dict.jasper_doc_id
	#module_path = os.path.normpath(os.path.join(os.path.dirname(jasper_erpnext_report.__file__), "public", "reports", frappe.local.site , jasper_doc_id))
	#module_path = os.path.normpath(os.path.join(os.path.dirname(jasper_erpnext_report.__file__), "reports", frappe.local.site , jasper_doc_id))
	#content = frappe.read_file(module_path, raise_not_found=True)
	#body = re.findall(rg, content)
	#body = re.findall(r'<body\b[^>]*>(.*)</body>', content, re.DOTALL)
	print "get_context url 5 {}".format(jasper_report_path)
	return {
		"jasper_report_path": "/assets/" + jasper_report_path#frappe.utils.cstr(body)
	}

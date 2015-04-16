from __future__ import unicode_literals
__author__ = 'luissaguas'

import frappe
import frappe.utils
from frappe import _

import jasper_erpnext_report.utils.utils

jasper_report_types = ['jasper_print_pdf', 'jasper_print_rtf', 'jasper_print_docx', 'jasper_print_ods',
						'jasper_print_odt', 'jasper_print_xls', 'jasper_print_all']


def do_doctype_from_jasper(data, reports, force=False):

	docs = []
	p_idx = 0
	for key, mydict in reports.iteritems():
		c_idx = 0
		p_idx = p_idx + 1
		uri = mydict.get("uri")
		ignore = False
		report_name = key
		change_name = False
		#if already exists check if has the same path (same report)
		old_names = frappe.db.sql("""select name, jasper_report_path, modified from `tabJasper Reports` where jasper_report_name='%s'""" % (key,), as_dict=1)
		for obj in old_names:
			if uri == obj.get('jasper_report_path'):
				change_name = False
				if data.get('import_only_new'):
					ignore = True
					break
				else:
					#no need to change if the same date or was changed locally by Administrator. Use force to force update and lose the changes
					time_diff = frappe.utils.time_diff_in_seconds(obj.get('modified'), mydict.get("updateDate"))
					if time_diff >= 0 and not force:
						ignore = True
					else:
						#set to the same name that is in db
						report_name = obj.name
					break
			else:
				#report with same name, must change
				change_name = True
		if ignore:
			continue

		if change_name:
			report_name = key + "#" + str(len(old_names))
		if True in [report_name == o.get("name") for o in docs]:
			report_name = key + "#" + str(p_idx)
		doc = frappe.new_doc("Jasper Reports")

		doc.name = report_name
		doc.jasper_report_name = key
		doc.jasper_report_path = uri
		doc.idx = p_idx
		doc.jasper_report_origin = "JasperServer"
		doc.jasper_all_sites_report = 0
		doc.jasper_email = 1
		doc.jasper_dont_show_report = 0
		for t in jasper_report_types:
			doc.set(t,data.get(t))

		if "double" in uri.lower():
			doc.jasper_report_number_copies = "Duplicated"
		elif "triple" in uri.lower():
			doc.jasper_report_number_copies = "Triplicate"
		else:
			doc.jasper_report_number_copies = data.get("report_default_number_copies")

		if "doctypes" in uri.lower():
			doctypes = uri.strip().split("/")
			doctype_name = doctypes[doctypes.index("doctypes") + 1]
			doc.jasper_report_type = "Form"
		else:
			doc.jasper_report_type = "General"
			doctype_name = None

		doc.jasper_doctype = doctype_name
		doc.query = mydict.get("queryString")
		doc.jasper_param_message = data.get('jasper_param_message').format(report=key, user=frappe.local.session['user'])#_("Please fill in the following parameters in order to complete the report.")
		jasper_doc = frappe._dict({"parent_doc": doc, "perm_docs":[], "param_docs":[]})


		for v in mydict.get('inputControls'):
			c_idx = c_idx + 1
			name = v.get('label')
			doc_params = set_jasper_parameters(name, key, c_idx, mydict)
			jasper_doc.param_docs.append(doc_params)


		doc_perms = set_jasper_permissions("JRPERM", key, 1)
		jasper_doc.perm_docs.append(doc_perms)
		docs.append(jasper_doc)

	#new docs must invalidate cache and db
	if docs:
		jasper_erpnext_report.utils.utils.jaspersession_set_value("report_list_dirt_all", True)
		jasper_erpnext_report.utils.utils.jaspersession_set_value("report_list_dirt_doc", True)


	return docs

def set_jasper_parameters(param_name, parent, c_idx, mydict, param_type="String"):
	action_type = "Ask"
	is_copy = "Other"
	param_expression = ""
	doc = frappe.new_doc("Jasper Parameter")
	#set the name here for support the same name from diferents reports
	#can't exist two params with the same name for the same report
	doc.name = parent + "_" + param_name#+ str(tot_idx)
	doc.jasper_param_name = param_name
	doc.idx = c_idx
	doc.jasper_param_type = param_type

	if jasper_erpnext_report.utils.utils.check_queryString_with_param(mydict.get("queryString"), param_name):
		is_copy = "Is for where clause"
		action_type = "Automatic"
		param_expression = "In"
	elif param_name in "where_not_clause":
		is_copy = "Is for where clause"
		action_type = "Automatic"
		param_expression = "Not In"
	elif param_name in "page_number":
		is_copy = "Is for page number"
		action_type = "Automatic"
	elif param_name in "for_copies":
		is_copy = "Is for copies"
		action_type = "Automatic"
	#doc name
	doc.is_copy = is_copy
	doc.jasper_param_action = action_type
	doc.jasper_param_description = ""
	doc.param_expression = param_expression

	doc.parent = parent#key
	doc.parentfield = "jasper_parameters"
	doc.parenttype = "Jasper Reports"


	return doc

def set_jasper_permissions(perm_name, parent, c_idx):
	doc = frappe.new_doc("Jasper PermRole")
	#set the name here for support the same name from diferents reports
	doc.name = parent + "_" + perm_name
	doc.idx = c_idx
	doc.jasper_role = "Administrator"
	doc.jasper_can_read = True
	doc.jasper_can_email = True

	doc.parent = parent
	doc.parentfield = "jasper_roles"
	doc.parenttype = "Jasper Reports"

	return doc
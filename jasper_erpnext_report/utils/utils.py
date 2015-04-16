from __future__ import unicode_literals
__author__ = 'luissaguas'
import frappe
import re
from frappe import _
from frappe.utils import cint, cstr
import logging
from frappe.modules.import_file import import_doc
from ast import literal_eval
from . cache import *
from . jasper_document import *
from . jasper_email import set_jasper_email_doctype

_logger = logging.getLogger(frappe.__name__)

jasper_formats = ["pdf", "docx", "xls","ods","odt", "rtf"]


def jasper_report_names_from_db(origin="both", filters_report={}, filters_param={}, filters_permrole={}):
	ret = None
	filters_param = filters_param.update({"parenttype":"Jasper Reports"})
	report_from = {"both":["jasperserver", "localserver"], "local jrxml only":["localserver"], "jasperserver only":["jasperserver"]}
	#get all report names
	rnames = frappe.get_all("Jasper Reports", debug=True, filters=filters_report, fields=["name","jasper_doctype", "report", "jasper_print_all", "jasper_print_docx", "jasper_report_origin",\
													"jasper_print_xls", "jasper_print_ods", "jasper_print_odt", "jasper_print_rtf", "jasper_print_pdf","jasper_dont_show_report",\
													"jasper_param_message", "jasper_report_type", "jasper_email", "jasper_locale"])
	with_param = frappe.get_all("Jasper Parameter", filters=filters_param, fields=["`tabJasper Parameter`.parent as parent", "`tabJasper Parameter`.name as p_name",\
													"`tabJasper Parameter`.jasper_param_name as name", "`tabJasper Parameter`.jasper_param_action",\
													"`tabJasper Parameter`.jasper_param_type", "`tabJasper Parameter`.jasper_param_value", "`tabJasper Parameter`.jasper_param_description",\
													"`tabJasper Parameter`.is_copy"])
	with_perm_role = frappe.get_all("Jasper PermRole", filters=filters_permrole, fields=["`tabJasper PermRole`.parent as parent", "`tabJasper PermRole`.name as p_name" ,"`tabJasper PermRole`.jasper_role", "`tabJasper PermRole`.jasper_can_read"])
	print "names in get from db 2 {} rnames {}".format(filters_report, rnames)
	if rnames:
		ret = {}
		for r in rnames:
			jasper_report_origin = r.jasper_report_origin.lower()
			print "newdata {} origin {} origin {}".format(jasper_report_origin, report_from.get(origin), origin)
			if jasper_report_origin in report_from.get(origin) and not r.jasper_dont_show_report:
				ret[r.name] = {"Doctype name": r.jasper_doctype, "report": r.report, "formats": jasper_print_formats(r),"params":[], "perms":[], "message":r.jasper_param_message,\
							   "jasper_report_type":r.jasper_report_type, "jasper_report_origin": r.jasper_report_origin, "email": r.jasper_email, "locale":r.jasper_locale}
				for report in with_param:
						name = report.parent
						if name == r.name:
							report.pop("parent")
							if report.jasper_param_action == "Automatic":
								continue
							report.pop("p_name")
							report.pop("jasper_param_action")
							ret[r.name]["params"].append(report)

				for perm in with_perm_role:
						name = perm.parent
						if name == r.name:
							perm.pop("parent")
							ret[r.name]["perms"].append(perm)

	return ret

def jasper_print_formats(doc):
	ret = []
	if int(doc.jasper_print_all) == 0:
		for fmt in jasper_formats:
			if int(doc.get("jasper_print_" + fmt,0) or 0) == 1:
				ret.append(fmt)
	else:
		ret = jasper_formats

	return ret

def validate_print_permission(doc):
	for ptype in ("read", "print"):
		if not frappe.has_permission(doc.doctype, ptype, doc):
			raise frappe.PermissionError(_("You don't have {0} permission.").format(ptype))

def import_all_jasper_remote_reports(docs, force=True):
	frappe.only_for("Administrator")
	frappe.flags.in_import = True
	for d in docs:
		import_doc(d.parent_doc.as_dict(), force=force)
		for param_doc in d.param_docs:
			import_doc(param_doc.as_dict(), force=force)
		for perm_doc in d.perm_docs:
			import_doc(perm_doc.as_dict(), force=force)

	frappe.flags.in_import = False


def check_queryString_with_param(query, param):
	ret = False
	s = re.search(r'\$P{%s}|\$P!{%s}|\$X{[\w\W]*,[\w\W]*, %s}' % (param, param, param), query, re.I)
	if s:
		ret = True
	return ret

def check_queryString_param(query, param):
	ret = check_queryString_with_param(query, param)

	return ret

def get_default_param_value(param, error=True):
	#if not data and not entered value then get default
	default_value = param.jasper_param_value
	if not default_value:
		if error:
			frappe.throw(_("Error, parameter {} needs a value.").format(param.jasper_param_name))
		else:
			return
	matchObj =re.match(r"^[\"'](.*)[\"']", default_value)
	if matchObj:
		default_value = matchObj.group(1)
	if default_value.startswith("(") or default_value.startswith("[") or default_value.startswith("{"):
		value = literal_eval(default_value)
	else:
		#this is the case when user enter "Administrator" and get translated to "'Administrator'"
		#then we need to convert to "Administrator" or 'Administrator'
		value = default_value
	return value

#call hooks for params set as "Is for server hook"
def call_hook_for_param(doc, method, *args):
	ret = doc.run_method(method, *args)
	return ret


def check_jasper_perm(perms, ptypes=("read",), user=None):
		found = False

		if isinstance(ptypes, basestring):
			ptypes = (ptypes, )

		if user == None:
			user = frappe.local.session['user']

		def check_perm(perms, user_roles, ptype):
			found = False
			for perm in perms:
				jasper_perm_type = perm.get('jasper_can_' + ptype, None)
				jasper_role = perm.get('jasper_role', None)
				if jasper_role in user_roles and jasper_perm_type:
					found = True
					break
			return found

		if user == "Administrator":
			return True

		user_roles = frappe.get_roles(user)

		for ptype in ptypes:
			found = check_perm(perms, user_roles, ptype)
			if found == False:
				break

		return found

def check_frappe_permission(doctype, docname, ptypes=("read", )):
	if isinstance(ptypes, basestring):
		ptypes = (ptypes, )
	perm = True
	for ptype in ptypes:
		if not frappe.has_permission(doctype, ptype=ptype, doc=docname, user=frappe.local.session['user']):
			perm = False
			break
	return perm


#select name, email from tabUser
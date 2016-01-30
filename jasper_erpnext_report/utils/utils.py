from __future__ import unicode_literals
__author__ = 'luissaguas'
import frappe
import re
from frappe import _
from frappe.modules.import_file import import_doc
from ast import literal_eval
from . cache import *
from . jasper_document import *
from . jasper_email import set_jasper_email_doctype
import jasper_erpnext_report
from jasper_erpnext_report.utils.jasper_iter_hooks import JasperHooks

jasper_formats = ["pdf", "docx", "xls","ods","odt", "rtf"]


def jasper_report_names_from_db(origin="both", filters_report=None, filters_param=None, filters_permrole=None):
	ret = None
	if filters_param:
		filters_param = filters_param.update({"parenttype":"Jasper Reports"})
	report_from = {"both":["jasperserver", "localserver"], "local jrxml only":["localserver"], "jasperserver only":["jasperserver"]}
	#get all report names
	rnames = frappe.get_all("Jasper Reports", debug=False, filters=filters_report, fields=["name","jasper_doctype", "report", "jasper_print_all", "jasper_print_docx", "jasper_report_origin",
													"jasper_print_xls", "jasper_print_ods", "jasper_print_odt", "jasper_print_rtf", "jasper_print_pdf","jasper_dont_show_report",
													"jasper_param_message", "jasper_report_type", "jasper_email", "jasper_locale", "jasper_dont_ask_for_params"])
	with_param = frappe.get_all("Jasper Parameter", filters=filters_param, fields=["`tabJasper Parameter`.parent as parent", "`tabJasper Parameter`.name as p_name",
													"`tabJasper Parameter`.jasper_param_name as name", "`tabJasper Parameter`.jasper_param_action",
													"`tabJasper Parameter`.jasper_param_type", "`tabJasper Parameter`.jasper_param_value", "`tabJasper Parameter`.jasper_param_description",
													"`tabJasper Parameter`.is_copy", "`tabJasper Parameter`.jasper_field_doctype"])
	with_perm_role = frappe.get_all("Jasper PermRole", filters=filters_permrole, fields=["`tabJasper PermRole`.parent as parent", "`tabJasper PermRole`.name as p_name" ,"`tabJasper PermRole`.jasper_role", "`tabJasper PermRole`.jasper_can_read"])
	if rnames:
		ret = {}
		size = 0
		for r in rnames:
			jasper_report_origin = r.jasper_report_origin.lower()
			if jasper_report_origin in report_from.get(origin) and not r.jasper_dont_show_report:
				ret[r.name] = {"Doctype name": r.jasper_doctype, "report": r.report, "formats": jasper_print_formats(r),"params":[], "perms":[], "message":r.jasper_param_message,
							   "jasper_report_type":r.jasper_report_type, "jasper_report_origin": r.jasper_report_origin, "email": r.jasper_email, "locale":r.jasper_locale\
								if jasper_report_origin=="localserver" else "not Ask", "show_params_dialog": not r.jasper_dont_ask_for_params}
				size += 1
				for report in with_param:
						name = report.parent
						if name == r.name:
							if report.jasper_param_action == "Automatic":
								break
							report.pop("parent")
							report.pop("p_name")
							report.pop("jasper_param_action")
							ret[r.name]["params"].append(report)
							break

				for perm in with_perm_role:
						name = perm.parent
						if name == r.name:
							perm.pop("parent")
							ret[r.name]["perms"].append(perm)
		ret["size"] = size
		ret["origin"] = origin
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
	if not docs:
		return
	frappe.flags.in_import = True
	for d in docs:
		import_doc(d.parent_doc.as_dict(), force=force)
		for param_doc in d.param_docs:
			import_doc(param_doc.as_dict(), force=force)
		for perm_doc in d.perm_docs:
			import_doc(perm_doc.as_dict(), force=force)
		#frappe.db.commit()

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
		if isinstance(default_value, basestring):
			value = default_value.replace("\"","").replace("'","")
		else:
			value = default_value
	return value

#call hooks for params set as "Is for server hook"
def call_hook_for_param(doc, method, *args):
	ret = doc.run_method(method, *args)
	return ret

#call hooks for params set as "Is for server hook"
def call_hook_for_param_with_default(doc, hook_name, *args):
	method = jasper_run_method_once_with_default(hook_name, doc.name, None)
	if method:
		ret = method(doc, *args)
	else:
		ret = call_hook_for_param(doc, hook_name, *args)
	return ret

"""
def testHookReport(doc, args1, args2):
	a = []
	a.append({"name": "idade", "value": 35.6})
	return a
"""

"""
This hook (jasper_scriptlet) must return an object that implements all the methods of JRAbstractScriptlet.
If you do not want to implement all the methods then you should extends JasperCustomScripletDefault of jasper_erpnext_report.jasper_reports.ScriptletDefault module.
If you extend then you should only implement the methods that you want.
The methods are: see JasperCustomScripletDefault in jasper_erpnext_report.jasper_reports.ScriptletDefault module.
It is possible to call any method from jrxml file. The test method bellow is one example.
"""
def testHookScriptlet(JasperScriptlet, ids, data, cols, cur_doctype, cur_docname):
	from jasper_erpnext_report.jasper_reports.ScriptletDefault import JasperCustomScripletDefault
	class MyJasperCustomScripletDefault(JasperCustomScripletDefault):
		def __init__(self, JasperScriplet, ids=None, data=None, cols=None, doctype=None):
			super(MyJasperCustomScripletDefault, self).__init__(JasperScriplet, ids, data, cols, doctype)

		def test(self, args):
			print "MyJasperCustomScripletDefault method Teste {}".format(args)
			return 10

	print "testHookScriptlet Curr_doctype {} Curr_docname {}".format(cur_doctype, cur_docname)
	return MyJasperCustomScripletDefault(JasperScriptlet, ids, data, cols, cur_doctype)

def get_make_jasper_hooks_path():
	jasper_hooks_path = frappe.get_site_path("jasper_hooks")
	frappe.create_folder(jasper_hooks_path, with_init=True)
	return jasper_hooks_path

def get_hook_module(hook_name, report_name=None):
	"""
		check if there is a scriptlet hook for this report in frappe-bench/sites/site_name/jasper_hooks folder.
		The folder have the following structure where jasper_hooks is the root(package):
			jasper_hooks/report name/hook name.py
			Example: jasper_hooks/Table 1 Custom/jasper_scriptlet.py -> where Table 1 Custom is the name of report and jasper_scriptlet.py
			is the name of the hook.
		Note: All the folders must have __init__.py to make it a package
		This strucutre is to help development. There is no need to make a frappe app only to control reports.
	"""
	import os, sys

	try:
		jasper_hooks_path = get_make_jasper_hooks_path()

		jasper_absolute_path = os.path.realpath(os.path.join(jasper_hooks_path))

		if jasper_absolute_path not in sys.path:
			sys.path.insert(0, jasper_absolute_path)

		report_name = report_name + "." if report_name else ""

		hook_module = frappe.get_module(report_name + hook_name)
	except:
		hook_module = None

	return hook_module

def jasper_run_method(hook_name, *args, **kargs):
	mlist = JasperHooks(hook_name)
	if mlist.methods_len > 0:
		for method in JasperHooks(hook_name):
			method(hook_name, *args, **kargs)
	else:
		hook_module = get_hook_module(hook_name)
		if hook_module:
			hook_module.get_data(*args, **kargs)

#call hooks for jasper custom data source
def jasper_run_method_once_with_default(hook_name, docname, default):
	m = JasperHooks(hook_name, docname, default)
	method = m.get_next_jasper_hook_method()
	return method

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

def jasper_users_login(user):

	s = jaspersession_get_value("jasper_list_user") or ";"
	if user not in s:
		s += user + ";"
		jaspersession_set_value("jasper_list_user", s)


#install module to rest in jasperreports server
def pipInstall(package=None):
	import sys
	import jasper_erpnext_report as jr
	package = package or "git+https://github.com/saguas/jasperserverlib.git"
	try:
		frappe.utils.execute_in_shell("../env/bin/pip install " + package)
		reload(sys.modules['jasper_erpnext_report.core.JasperServer'])
	except Exception as e:
		jr.jasperserverlib = False
		frappe.msgprint(_("Error when install package {}. Error: {}".format(package, e)))


def get_Frappe_Version(version=None):
	version = version or frappe.__version__
	import semantic_version as sv
	return sv.Version(version)

def getFrappeVersion():
	return jasper_erpnext_report.FRAPPE_VERSION

def add_to_time_str(date=None, hours=0, days=0, weeks=0):
	from datetime import timedelta
	date = date or frappe.utils.now()
	d = frappe.utils.get_datetime(date) + timedelta(hours=hours, days=days, weeks=weeks)
	new_date = frappe.utils.get_datetime_str(d)
	return new_date

class FrappeContext:

	def __init__(self, site, user):
		self.site = site
		self.user = user

	def __enter__(self):
		frappe.init(site=self.site)
		frappe.connect()
		print frappe.local.site
		frappe.set_user(self.user)

	def __exit__(self, type, value, trace):
		if frappe.db:
			frappe.db.commit()

		frappe.destroy()
from __future__ import unicode_literals
__author__ = 'luissaguas'
import frappe
import re
from frappe import _
from frappe.utils import cint, cstr
import logging
from frappe.modules.import_file import import_doc
from ast import literal_eval


_logger = logging.getLogger(frappe.__name__)

jasper_formats = ["pdf", "docx", "xls","ods","odt", "rtf"]
jasper_report_types = ['jasper_print_pdf', 'jasper_print_rtf', 'jasper_print_docx', 'jasper_print_ods',\
						'jasper_print_odt', 'jasper_print_xls', 'jasper_print_all']

jasper_cache_data = [{"mcache":"jaspersession", "db": "tabJasperSessions"},{"mcache":'report_list_all', "db": None},\
					{"mcache":'report_list_doctype', "db": None}]

def before_install():
	frappe.db.sql_ddl("""CREATE TABLE IF NOT EXISTS tabJasperSessions(
		user varchar(255) DEFAULT NULL,
		sessiondata longtext,
		lastupdate datetime(6) DEFAULT NULL,
		status varchar(20) DEFAULT NULL
		)""")

	frappe.db.sql_ddl("""CREATE TABLE IF NOT EXISTS tabJasperReqids(
		reqid varchar(255) DEFAULT NULL,
		data longtext,
		lastupdate datetime(6) DEFAULT NULL,
		KEY reqid (reqid)
		)""")


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
													"`tabJasper Parameter`.jasper_param_type", "`tabJasper Parameter`.jasper_param_value", "`tabJasper Parameter`.jasper_param_description"])
	with_perm_role = frappe.get_all("Jasper PermRole", filters=filters_permrole, fields=["`tabJasper PermRole`.parent as parent", "`tabJasper PermRole`.name as p_name" ,"`tabJasper PermRole`.jasper_role", "`tabJasper PermRole`.jasper_can_read"])
	if rnames:
		ret = {}
		for r in rnames:
			jasper_report_origin = r.jasper_report_origin.lower()
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

def insert_jasper_list_all(data, cachename="report_list_all", tab="tabJasperReportListAll"):
		jaspersession_set_value(cachename, data)

def insert_list_all_memcache_db(data, cachename="report_list_all", tab="tabJasperReportListAll", fields={}):
	data['session_expiry'] = get_expiry_period(sessionId=cachename)
	data['last_updated'] = frappe.utils.now()
	for k,v in fields.iteritems():
		data[k] = v
	try:
		insert_jasper_list_all({"data":data}, cachename, tab)
	except:
		pass

def update_jasper_list_all(data, cachename="report_list_all", tab="tabJasperReportListAll"):
		# also add to memcache
		jaspersession_set_value(cachename, data)

def update_list_all_memcache_db(data, cachename="report_list_all", tab="tabJasperReportListAll", fields={}):
	data['session_expiry'] = get_expiry_period(sessionId=cachename)
	data['last_updated'] = frappe.utils.now()
	old_data = frappe._dict(jaspersession_get_value(cachename) or {})
	new_data = old_data.get("data", {})
	new_data.update(data)
	for k,v in fields.iteritems():
		new_data[k] = v
	update_jasper_list_all({"data":new_data}, cachename, tab)


def get_jasper_data(cachename, get_from_db=None, *args, **kargs):

		if frappe.local.session['sid'] == 'Guest':
			return None
		data = get_jasper_session_data_from_cache(cachename)
		if not data:
			data = get_jasper_data_from_db(get_from_db, *args, **kargs)
			if data:
				#if there is data in db but not in cache then update cache
				user = data.get("user")
				if user:
					d = frappe._dict({'data': data, 'user':data.get("user")})
				else:
					d = frappe._dict({'data': data})
				jaspersession_set_value(cachename, d)
		return data

def get_jasper_session_data_from_cache(sessionId):
		data = frappe._dict(jaspersession_get_value(sessionId) or {})
		if data:
			session_data = data.get("data", {})
			time_diff, expiry = get_jasper_session_expiry_seconds(session_data.get("last_updated"), session_data.get("session_expiry"))
			if time_diff > expiry:
				_logger.info("JasperServerSession get_jasper_session_data_from_cache {}".format(sessionId))
				data = None

		return data and frappe._dict(data.data)

def get_jasper_session_expiry_seconds(last_update, session_expiry):
	time_diff = frappe.utils.time_diff_in_seconds(frappe.utils.now(),
		last_update)
	expiry = get_expiry_in_seconds(session_expiry)
	return time_diff, expiry


def get_jasper_data_from_db(get_from_db=None, *args, **kargs):
	if not get_from_db:
		rec = get_jasper_session_data_from_db()
	elif args:
		rec = get_from_db(*args)
	elif kargs:
		nargs = kargs.get("args", None)
		if nargs:
			rec = get_from_db(*nargs)
		else:
			rec = get_from_db(**kargs)
	else:
		rec = get_from_db()

	if rec:
		try:
			data = frappe._dict(eval(rec and rec[0][1] or '{}'))
		except:
			data = None
	else:
		data = None
	return data

def get_jasper_session_data_from_db():
	rec = frappe.db.sql("""select user, sessiondata
		from tabJasperSessions where
		TIMEDIFF(NOW(), lastupdate) < TIME("{0}") and status='Active'""".format(get_expiry_period("jaspersession")))
	return rec

def jaspersession_get_value(sessionId):
	return frappe.cache().get_value("jasper:" + sessionId)

def jaspersession_set_value(sessionId, data):
	frappe.cache().set_value("jasper:" + sessionId, data)

def delete_jasper_session(sessionId, tab="tabJasperSessions", where=None):

	frappe.cache().delete_value("jasper:" + sessionId)
	if tab and where:
		frappe.db.sql("""delete from {} where {}""".format(tab, where))
	elif tab:
		frappe.db.sql("""delete from {}""".format(tab))

	if tab:
		frappe.db.commit()

def get_expiry_in_seconds(expiry):
		if not expiry: return 3600
		parts = expiry.split(":")
		return (cint(parts[0]) * 3600) + (cint(parts[1]) * 60) + cint(parts[2])

def validate_print_permission(doc):
	for ptype in ("read", "print"):
		if not frappe.has_permission(doc.doctype, ptype, doc):
			raise frappe.PermissionError(_("No {0} permission").format(ptype))

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
		jaspersession_set_value("report_list_dirt_all", True)
		jaspersession_set_value("report_list_dirt_doc", True)

	_logger.info("jasperserver make_doctype_from_jasper {}".format(docs))

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

	if check_queryString_with_param(mydict.get("queryString"), param_name):
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

def set_jasper_email_doctype(parent_name, sent_to, sender, when, filepath, filename):
	from frappe.model.naming import make_autoname

	jer_doc = frappe.new_doc('Jasper Email Report')

	jer_doc.jasper_email_report_name = parent_name
	jer_doc.name = make_autoname(parent_name + '/.DD./.MM./.YY./.#######')
	jer_doc.jasper_email_sent_to = sent_to
	jer_doc.jasper_email_sender = sender
	jer_doc.jasper_email_date = when
	jer_doc.jasper_file_name = filename
	jer_doc.jasper_report_path = filepath
	jer_doc.idx = cint(frappe.db.sql("""select max(idx) from `tabJasper Email Report`""")[0][0]) + 1

	jer_doc.ignore_permissions = True
	jer_doc.insert()

	return jer_doc



def check_queryString_with_param(query, param):
	ret = False
	s = re.search(r'\$P{%s}|\$P!{%s}|\$X{[\w\W]*,[\w\W]*, %s}' % (param, param, param), query, re.I)
	if s:
		ret = True
	return ret

def check_queryString_param(query, param):
	ret = check_queryString_with_param(query, param)

	return ret

def get_expiry_period(sessionId="jaspersession"):
	reports_names = ["report_list_doctype", "report_list_all"]
	if sessionId in reports_names:
		exp_sec = "24:00:00"
	elif "intern_reqid_" in sessionId or "local_report_" in sessionId:
		exp_sec = "8:00:00"
	elif "client_html_" in sessionId:
		exp_sec = "00:10:00"
	else:
		exp_sec = frappe.defaults.get_global_default("jasper_session_expiry") or "12:00:00"

		#incase seconds is missing
		if len(exp_sec.split(':')) == 2:
			exp_sec = exp_sec + ':00'
	return exp_sec

def get_value_param_for_hook(param, error=True):
	#if not data and not entered value then get default
	default_value = param.jasper_param_value
	if not default_value:
		if error:
			frappe.throw(_("Error, parameter {} needs a value!").format(param.jasper_param_name))
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

"""
def jasper_params(doc, method, data, params):
	for param in params:
		if param.get('name') != "name_ids":
			attrs = param.get("attrs")
			default_value = param.get("value")
			a = ["'%s'" % t for t in default_value]
			value = "where name %s (%s)" % (attrs.param_expression, ",".join(a))
			if not default_value:
				default_value.append(value)
			else:
				param['value'] = [value]
		else:
			param['value'].append('Guest')

	return params
"""

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
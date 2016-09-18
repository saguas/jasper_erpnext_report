from __future__ import unicode_literals
__author__ = 'luissaguas'
from frappe import _
import frappe
import frappe.async
import json
from urllib2 import unquote
import time
from frappe.utils import cint

import jasper_erpnext_report, os

import JasperRoot as Jr
from jasper_erpnext_report import jasper_session_obj
from jasper_erpnext_report.core.JasperRoot import get_copies

from jasper_erpnext_report.utils.utils import set_jasper_email_doctype, check_frappe_permission, jasper_run_method,\
	jasper_users_login, jaspersession_set_value, pipInstall, getFrappeVersion
from jasper_erpnext_report.utils.jasper_email import jasper_save_email, get_sender, get_email_pdf_path, get_email_other_path, sendmail, sendmail_v5
from jasper_erpnext_report.utils.file import get_file, get_html_reports_path, write_file
from jasper_erpnext_report.utils.cache import redis_transation


_logger = frappe.logger("jasper_erpnext_report")


def boot_session(bootinfo):
	bootinfo['jasper_reports_list'] = get_reports_list_for_all()
	arr = getLangInfo()
	bootinfo["langinfo"] = arr

def getLangInfo():
	arr = []
	version = cint(frappe.__version__.split(".", 1)[0])
	if version < 5:
		from frappe.translate import get_lang_info
		langinfo = get_lang_info()
		for l in langinfo:
			obj = {}
			some_list = l.split("\t")
			b = [frappe.utils.cstr(a).strip() for a in filter(None, some_list)]
			try:
				obj["name"] = b[1]
				obj["code"] = b[0]
			except:
				obj["name"] = ""
				pass
			arr.append(obj)
	else:
		from frappe.geo.country_info import get_all
		langinfo = get_all()
		for k,v in langinfo.iteritems():
			obj = {}
			obj["name"] = k
			obj["code"] = v.get("code")
			arr.append(obj)

	return arr

@frappe.whitelist()
def get_reports_list_for_all():
	jasper_run_method("jasper_before_list_for_all")
	jsr = jasper_session_obj or Jr.JasperRoot()
	jasper_users_login(jsr.user)
	lall = jsr.get_reports_list_for_all()
	jasper_run_method("jasper_after_list_for_all", lall)
	return lall

@frappe.whitelist()
def get_reports_list(doctype, docnames, report):
	jsr = jasper_session_obj or Jr.JasperRoot()
	jasper_run_method("jasper_before_list_for_doctype", doctype, docnames, report)
	jasper_users_login(jsr.user)
	l = jsr.get_reports_list(doctype, docnames, report)
	jasper_run_method("jasper_after_list_for_doctype", doctype, docnames, report, l)
	return l

@frappe.whitelist()
def report_polling(data):
	jsr = jasper_session_obj or Jr.JasperRoot()
	return jsr.report_polling(data)

@frappe.whitelist()
def get_report(data):
	if not data:
		frappe.throw(_("There is no data for this Report."))

	if isinstance(data, basestring):
		data = json.loads(unquote(data))

	if data.get("origin") == "local":
		list_data = frappe.call(report_polling, data)
		if not list_data:
			frappe.throw("Your report was not found!. Please try again.")
		data = list_data[0]

	pformat = data.get("pformat")
	fileName, content, report_name = _get_report(data)
	return make_pdf(fileName, content, pformat, report_name, reqId=data.get("requestId"))

def _get_report(data):
	jasper_run_method("jasper_before_get_report", data)
	jsr = jasper_session_obj or Jr.JasperRoot()
	fileName, content, report_name = jsr.get_report_server(data)
	pformat = data.get("pformat")
	if pformat == "html":
		html_reports_path = get_html_reports_path(report_name, hash=jsr.html_hash)
		write_file(content[0], os.path.join(html_reports_path, fileName))

	return fileName, content, report_name

def getHtmlFilepath(report_name, fileName):
	jsr = jasper_session_obj or Jr.JasperRoot()
	path_jasper_module = os.path.dirname(jasper_erpnext_report.__file__)
	html_reports_path = get_html_reports_path(report_name, hash=jsr.html_hash)
	full_path = os.path.join(html_reports_path, fileName)
	relat_path = os.path.relpath(full_path, os.path.join(path_jasper_module, "public"))
	return os.path.join("jasper_erpnext_report",relat_path)

def getPdfFilePath(file_name, filepath):

	down = os.path.normpath(os.path.join(os.path.dirname(jasper_erpnext_report.__file__), "public", "reports", frappe.local.site))
	norm = os.path.normpath(os.path.relpath(filepath, down))
	path = os.path.join(norm, file_name)
	return path

def make_pdf(fileName, content, pformat, report_name, reqId=None, merge_all=True, pages=None, email=False):

	if pformat == "html":
		filepath = getHtmlFilepath(report_name, fileName)
		g = "jasper_erpnext_report/reports/" + frappe.local.site
		path = os.path.normpath(os.path.relpath(filepath, g))
		url = "%s?jasper_doc_path=%s" % ("Jasper Reports", path)
		fileName = fileName[fileName.rfind(os.sep) + 1:]
		file_name = fileName.replace(" ", "-").replace("/", "-")
		jasper_run_method("jasper_after_get_report", file_name, content, url, filepath)
		if not email:
			return url
		return url, filepath

	jsr = jasper_session_obj or Jr.JasperRoot()
	file_name, output = jsr.make_pdf(fileName, content, pformat, merge_all, pages)

	if pformat == "pdf":
		filepath = get_email_pdf_path(report_name, reqId)
		path = getPdfFilePath(file_name, filepath)
		url = "%s?jasper_doc_path=%s" % ("Jasper Reports", path)
		jasper_run_method("jasper_after_get_report", file_name, output.getvalue(), url, filepath)
		if not email:
			file_path = os.path.join(filepath, file_name)
			jasper_save_email(file_path, output.getvalue())
			return url
		return file_name, filepath, output, url

	jasper_run_method("jasper_after_get_report", file_name, output.getvalue(), None, None)
	if not email:
		jsr.prepare_file_to_client(file_name, output.getvalue())
		return

	return file_name, output

@frappe.whitelist()
#@frappe.async.handler
def run_report(data, docdata=None):
	if not data:
		frappe.throw("No data for this Report!!!")
	if isinstance(data, basestring):
		data = json.loads(data)

	frappe.local.task_id = data.pop("task_id")
	jsr = jasper_session_obj or Jr.JasperRoot()
	return jsr.run_report(data, docdata=docdata)

@frappe.whitelist()
def get_server_info():
	jsr = jasper_session_obj or Jr.JasperRoot()
	return jsr._get_server_info()

@frappe.whitelist()
def jasper_server_login(doc):
	doc = json.loads(doc)
	jsr = jasper_session_obj or Jr.JasperRoot(doc)
	checkJasperRestLib()
	login = jsr.login()
	#get the list of reports on the server
	#r_filters=["`tabJasper Reports`.jasper_doctype is NULL", "`tabJasper Reports`.report is NULL"]
	r_filters = {"jasper_doctype": "", "report": ""}
	data = jsr._get_reports_list(filters_report=r_filters)
	cached = redis_transation(data, "report_list_all")
	if cached and data:
		jaspersession_set_value("report_list_dirt_doc", True)
		jaspersession_set_value("report_list_dirt_all", False)
	elif data:
		#redis not cache
		jaspersession_set_value("report_list_dirt_all", True)
		jaspersession_set_value("report_list_dirt_doc", True)

	return login

def checkJasperRestLib():
	from jasper_erpnext_report import jasperserverlib

	#TODO check for jasperserverlib folder in env
	if not jasperserverlib:
		pipInstall()

@frappe.whitelist()
def get_doc(doctype, docname):
	data = {}
	doc = frappe.get_doc(doctype, docname)
	if check_frappe_permission(doctype, docname, ptypes=("read", )):
		data = {"data": doc}
	frappe.local.response.update(data)

@frappe.whitelist()
def jasper_make_email(doctype=None, name=None, content=None, subject=None, sent_or_received = "Sent",
	sender=None, recipients=None, communication_medium="Email", send_email=False,
	print_html=None, print_format=None, attachments='[]', send_me_a_copy=False, set_lead=True, date=None,
	jasper_doc=None, docdata=None):

	custom_print_html = print_html
	custom_print_format = print_format

	jasper_polling_time = frappe.db.get_value('JasperServerConfig', fieldname="jasper_polling_time")
	data = json.loads(jasper_doc)
	result = run_report(data, docdata)
	if result[0].get("status", "not ready") != "ready":
		poll_data = prepare_polling(result)
		result = report_polling(poll_data)
		limit = 0
		while limit <= 10 and result[0].get("status", "not ready") != "ready":
			time.sleep(cint(jasper_polling_time)/1000)
			result = report_polling(poll_data)
			limit += 1

	pformat = data.get("pformat")
	#we have to remove the original and send only duplicate
	if result[0].get("status", "not ready") == "ready":
		rdoc = frappe.get_doc(data.get("doctype"), data.get('report_name'))
		ncopies = get_copies(rdoc, pformat)
		fileName, jasper_content, report_name = _get_report(result[0])
		merge_all = True
		pages = None
		if pformat == "pdf" and ncopies > 1:
			merge_all = False
			pages = get_pages(ncopies, len(jasper_content))

		sender = get_sender(sender)

		if pformat == "html":
			custom_print_html = True
			url, filepath = make_pdf(fileName, jasper_content, pformat, report_name, merge_all=merge_all, pages=pages, email=True)
			output = filepath
			file_name = output.rsplit("/",1)
			if len(file_name) > 1:
				file_name = file_name[1]
			else:
				file_name = file_name[0]


		elif pformat == "pdf":
			custom_print_format = "pdf"
			file_name, filepath, output, url = make_pdf(fileName, jasper_content, pformat, report_name, reqId=result[0].get("requestId"), merge_all=merge_all, pages=pages, email=True)
			output = output.getvalue()

		else:
			file_name, output = make_pdf(fileName, jasper_content, pformat, report_name, merge_all=merge_all, pages=pages, email=True)
			filepath = url = get_email_other_path(data, file_name, result[0].get("requestId"), sender)
			output = output.getvalue()
			#remove name from filepath
			filepath = filepath.rsplit("/",1)[0]

	else:
		frappe.throw(_("Error generating %s format, try again later.") % (pformat,))
		frappe.errprint(frappe.get_traceback())
		return

	if not check_frappe_permission(data.get("doctype"), data.get('report_name'), ptypes=("read", )):
		raise frappe.PermissionError((_("You are not allowed to send emails related to") + ": {doctype} {name}").format(
			doctype=data.get("doctype"), name=data.get('report_name')))

	jasper_run_method("jasper_before_sendmail", data, file_name, output, url, doctype=doctype, name=name, content=content, subject=subject, sent_or_received=sent_or_received,
		sender=sender, recipients=recipients, print_html=print_html, print_format=print_format, attachments=attachments,
		send_me_a_copy=send_me_a_copy)

	version = getFrappeVersion().major
	if version >= 5:
		file_path = None

		if isinstance(attachments, basestring):
			attachments = json.loads(attachments)

		if pformat != "html":
			file_path = os.path.join(filepath, file_name)
			jasper_save_email(file_path, output)
			attachments.append(file_path)

		comm_name = sendmail_v5(url, doctype=doctype, name=name, content=content, subject=subject, sent_or_received=sent_or_received,
				sender=sender, recipients=recipients, send_email=send_email, print_html=print_html, print_format=print_format, attachments=attachments)

		set_jasper_email_doctype(data.get('report_name'), recipients, sender, frappe.utils.now(), url, file_name)
		jasper_run_method("jasper_after_sendmail", data, url, file_name, file_path)

		return comm_name

	print_format = custom_print_format
	print_html = custom_print_html

	sendmail(file_name, output, url, doctype=doctype, name=name, content=content, subject=subject, sent_or_received=sent_or_received,
		sender=sender, recipients=recipients, print_html=print_html, print_format=print_format, attachments=attachments,
		send_me_a_copy=send_me_a_copy)

	file_path = None
	if pformat != "html":
		file_path = os.path.join(filepath, file_name)
		jasper_save_email(file_path, output)

	set_jasper_email_doctype(data.get('report_name'), recipients, sender, frappe.utils.now(), url, file_name)
	jasper_run_method("jasper_after_sendmail", data, url, file_name, file_path)

def prepare_polling(data):
	d = data[0]
	poll_data = {"reqIds": [d.get("requestId")], "reqtime": d.get("reqtime"), "pformat": d.get("pformat"), "origin": d.get("origin")}
	return poll_data

def get_pages(ncopies, total_pages):
	pages = []
	clientes = total_pages/ncopies
	for n in range(clientes):
		pages.append(n*ncopies)

	return pages

@frappe.whitelist()
def get_jasper_email_report(data):
	if not data:
		frappe.throw(_("There is no data for this Report."))
	data = json.loads(unquote(data))
	file_name = data.get("filename")
	file_path = data.get("filepath")
	jsr = jasper_session_obj or Jr.JasperRoot()
	try:
		output = get_file(file_path, modes="rb")
		jsr.prepare_file_to_client(file_name, output)
	except:
		frappe.throw(_("There is no %s report." % file_name))


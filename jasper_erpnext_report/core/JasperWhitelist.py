from __future__ import unicode_literals
__author__ = 'luissaguas'
from frappe import _
import frappe
import json
from urllib2 import unquote
import logging, time
from frappe.utils import cint
from jasper_erpnext_report.utils.file import get_html_reports_path, write_file

import jasper_erpnext_report, os

import JasperRoot as Jr
from jasper_erpnext_report import jasper_session_obj
from jasper_erpnext_report.utils.jasper_email import sendmail
from jasper_erpnext_report.core.JasperRoot import get_copies

from jasper_erpnext_report.utils.utils import set_jasper_email_doctype, check_frappe_permission
from jasper_erpnext_report.utils.jasper_email import jasper_save_email, get_sender
from jasper_erpnext_report.utils.file import get_file

_logger = logging.getLogger(frappe.__name__)


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
			obj["name"] = b[1]
			obj["code"] = b[0]
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
	jsr = jasper_session_obj or Jr.JasperRoot()
	return jsr.get_reports_list_for_all()

@frappe.whitelist()
def get_reports_list(doctype, docnames, report):
	jsr = jasper_session_obj or Jr.JasperRoot()
	return jsr.get_reports_list(doctype, docnames, report)

@frappe.whitelist()
def report_polling(data):
	jsr = jasper_session_obj or Jr.JasperRoot()
	return jsr.report_polling(data)

@frappe.whitelist()
def get_report(data):

	if not data:
		frappe.throw(_("No data for this Report!!!"))
	if isinstance(data, basestring):
		data = json.loads(unquote(data))
	pformat = data.get("pformat")
	fileName, content, report_name = _get_report(data)
	return make_pdf(fileName, content, pformat, report_name)

def _get_report(data):
	jsr = jasper_session_obj or Jr.JasperRoot()
	fileName, content, report_name = jsr.get_report_server(data)
	pformat = data.get("pformat")
	if pformat == "html":
		html_reports_path = get_html_reports_path(report_name, hash=jsr.html_hash)
		write_file(content[0], os.path.join(html_reports_path, fileName))

	return fileName, content, report_name

def make_pdf(fileName, content, pformat, report_name, merge_all=True, pages=None, email=False):
	jsr = jasper_session_obj or Jr.JasperRoot()
	file_name, output = jsr.make_pdf(fileName, content, pformat, merge_all, pages)
	#if not email:
	if pformat == "html":
		path_jasper_module = os.path.dirname(jasper_erpnext_report.__file__)
		html_reports_path = get_html_reports_path(report_name, hash=jsr.html_hash)
		full_path = os.path.join(html_reports_path, fileName)
		relat_path = os.path.relpath(full_path, os.path.join(path_jasper_module, "public"))
		return os.path.join("jasper_erpnext_report",relat_path)
	if not email:
		jsr.prepare_file_to_client(file_name, output.getvalue())
		return

	return file_name, output

@frappe.whitelist()
def run_report(data, docdata=None):
	if not data:
		frappe.throw("No data for this Report!!!")
	if isinstance(data, basestring):
		data = json.loads(data)
	jsr = jasper_session_obj or Jr.JasperRoot()
	return jsr.run_report(data, docdata=docdata)

@frappe.whitelist()
def get_server_info():
	jsr = jasper_session_obj or Jr.JasperRoot()
	return jsr._get_server_info()

@frappe.whitelist()
def jasper_server_login():
	jsr = jasper_session_obj or Jr.JasperRoot()
	return jsr.login()

@frappe.whitelist()
def get_doc(doctype, docname):
	data = {}
	doc = frappe.get_doc(doctype, docname)
	if check_frappe_permission(doctype, docname, ptypes=("read", )):
		data = {"data": doc}
	frappe.local.response.update(data)

@frappe.whitelist()
def jasper_make(doctype=None, name=None, content=None, subject=None, sent_or_received = "Sent",
	sender=None, recipients=None, communication_medium="Email", send_email=False,
	print_html=None, print_format=None, attachments='[]', send_me_a_copy=False, set_lead=True, date=None,
	jasper_doc=None, docdata=None):

	jasper_polling_time = frappe.db.get_value('JasperServerConfig', fieldname="jasper_polling_time")
	data = json.loads(jasper_doc)
	result = run_report(data, docdata)
	if result[0].get("status", "not ready") != "ready":
		poll_data = prepare_polling(result)
		result = report_polling(poll_data)
		limit = 0
		while not "status" in result[0] and limit <= 10:
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

		filepath = None
		if pformat == "html":
			print_html = True
			filepath = output = make_pdf(fileName, jasper_content, pformat, report_name, merge_all=merge_all, pages=pages, email=True)
			file_name = output.rsplit("/",1)
			if len(file_name) > 1:
				file_name = file_name[1]
			else:
				file_name = file_name[0]

			#filepath = output
			#s = output.split("/",1)[1]
			#module_path = os.path.normpath(os.path.join(os.path.dirname(jasper_erpnext_report.__file__), "public", s))
			#print "email output html path module_path 8 {} file_name {} filepath {}".format(module_path, file_name, filepath)
			#output = frappe.read_file(module_path, raise_not_found=True)
		else:
			file_name, output = make_pdf(fileName, jasper_content, pformat, report_name, merge_all=merge_all, pages=pages, email=True)
			output = output.getvalue()

	else:
		frappe.throw(_("Error generating %s format, try again later") % (pformat,))
		frappe.errprint(frappe.get_traceback())
		return

	#perms = rdoc.get("jasper_roles")
	#TODO: must check for frappe permissions : jsr.check_frappe_permission(doctype, docname, ptypes=("email", )) and
	if not check_frappe_permission(data.get("doctype"), data.get('report_name'), ptypes=("read", )):
		raise frappe.PermissionError((_("You are not allowed to send emails related to") + ": {doctype} {name}").format(
			doctype=data.get("doctype"), name=data.get('report_name')))

	sender = get_sender(sender)
	sendmail(file_name, output, filepath, doctype=doctype, name=name, content=content, subject=subject, sent_or_received=sent_or_received,
		sender=sender, recipients=recipients, print_html=print_html, print_format=print_format, attachments=attachments,
		send_me_a_copy=send_me_a_copy)

	if pformat != "html":
		print "file_name in email make pdf 2 {}".format(file_name)
		filepath = jasper_save_email(data, file_name, output, result[0].get("requestId"), sender)

	set_jasper_email_doctype(data.get('report_name'), recipients, sender, frappe.utils.now(), filepath, file_name)

def prepare_polling(data):
	reqids = []
	for d in data:
		reqids.append(d.get("requestId"))
	poll_data = {"reqIds": reqids, "reqtime": d.get("reqtime"), "pformat": d.get("pformat"), "origin": d.get("origin")}
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
		frappe.throw(_("No data for this Report!!!"))
	data = json.loads(unquote(data))
	file_name = data.get("filename")
	file_path = data.get("filepath")
	jsr = jasper_session_obj or Jr.JasperRoot()
	try:
		output = get_file(file_path, modes="rb")
		jsr.prepare_file_to_client(file_name, output)
	except:
		frappe.throw(_("There is no %s report!!!" % file_name))


from __future__ import unicode_literals
__author__ = 'luissaguas'
from frappe import _
import frappe
import json
from urllib2 import unquote
import logging, time
from frappe.utils import cint

import jasper_erpnext_report, os
#from frappe.core.doctype.communication.communication import make

import JasperRoot as Jr
from jasper_erpnext_report import jasper_session_obj
from jasper_erpnext_report.utils.jasper_email import sendmail
from jasper_erpnext_report.core.JasperRoot import get_copies

from jasper_erpnext_report.utils.utils import set_jasper_email_doctype, check_jasper_perm
from jasper_erpnext_report.utils.jasper_email import jasper_save_email, get_sender
from jasper_erpnext_report.utils.file import get_file

_logger = logging.getLogger(frappe.__name__)


def boot_session(bootinfo):
	#bootinfo['jasper_server_info'] = get_server_info()
	bootinfo['jasper_reports_list'] = get_reports_list_for_all()


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
	#print "data get_reportssss {}".format(unquote(data))
	if not data:
		frappe.throw(_("No data for this Report!!!"))
	if isinstance(data, basestring):
		data = json.loads(unquote(data))
	pformat = data.get("pformat")
	fileName, content = _get_report(data)
	return make_pdf(fileName, content, pformat)

#def _get_report(data, merge_all=True, pages=None, email=False):
def _get_report(data):
	jsr = jasper_session_obj or Jr.JasperRoot()
	fileName, content = jsr.get_report_server(data)
	pformat = data.get("pformat")
	if pformat == "html":
		for c in content:
			from jasper_erpnext_report.utils.file import write_file
			path_jasper_module = os.path.dirname(jasper_erpnext_report.__file__)
			frappe.create_folder(os.path.join(path_jasper_module, "public", "reports", fileName.split(".")[0]))
			#print "frappe.local.request 3 {}".format(frappe.local.request.host_url)
			write_file(c, os.path.join(path_jasper_module, "public", "reports", fileName.split(".")[0], fileName))
	#file_name, output = jsr.make_pdf(fileName, content, pformat, merge_all, pages)
	#if not email:
	#	jsr.prepare_file_to_client(file_name, output)
	#	return

	#return file_name, output
	return fileName, content

def make_pdf(fileName, content, pformat, merge_all=True, pages=None, email=False):
	jsr = jasper_session_obj or Jr.JasperRoot()
	file_name, output = jsr.make_pdf(fileName, content, pformat, merge_all, pages)
	if not email:
		if pformat == "html":
			path_jasper_module = os.path.dirname(jasper_erpnext_report.__file__)
			full_path = os.path.join(path_jasper_module, "public", "reports", fileName.split(".")[0], fileName)
			relat_path = os.path.relpath(full_path, os.path.join(path_jasper_module, "public"))
			return os.path.join("jasper_erpnext_report",relat_path)
		jsr.prepare_file_to_client(file_name, output.getvalue())
		return

	return file_name, output

@frappe.whitelist()
def run_report(data, docdata=None):
	from frappe.utils import pprint_dict
	if not data:
		frappe.throw("No data for this Report!!!")
	if isinstance(data, basestring):
		data = json.loads(data)
	jsr = jasper_session_obj or Jr.JasperRoot()
	print "params in run_report 3 {}".format(pprint_dict(data))
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
	import jasper_erpnext_report.utils.utils as utils
	data = {}
	doc = frappe.get_doc(doctype, docname)
	if utils.check_jasper_perm(doc.get("jasper_roles", None)):
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
		#while result[0].get("status", "not ready") != "ready" and limit <= 10:
		while not "status" in result[0] and limit <= 10:
			time.sleep(cint(jasper_polling_time)/1000)
			result = report_polling(poll_data)
			limit += 1

	#we have to remove the original and send only duplicate
	if result[0].get("status", "not ready") == "ready":
		pformat = data.get("pformat")
		rdoc = frappe.get_doc(data.get("doctype"), data.get('report_name'))
		ncopies = get_copies(rdoc, pformat)
		#file_name, output = _get_report(result[0], merge_all=True, pages=None, email=True)
		fileName, jasper_content = _get_report(result[0])
		merge_all = True
		pages = None
		if pformat == "pdf" and ncopies > 1:
			merge_all = False
			pages = get_pages(ncopies, len(jasper_content))

		file_name, output = make_pdf(fileName, jasper_content, pformat, merge_all=merge_all, pages=pages, email=True)

	else:
		print "not sent by email... {}".format(result)
		frappe.throw(_("Error generating PDF, try again later"))
		frappe.errprint(frappe.get_traceback())
		return

	#attach = jasper_make_attach(data, file_name, output, attachments, result)

	#make(doctype=doctype, name=name, content=content, subject=subject, sent_or_received=sent_or_received,
	#	sender=sender, recipients=recipients, communication_medium=communication_medium, send_email=False,
	#	print_html=print_html, print_format=print_format, attachments=attachments, send_me_a_copy=send_me_a_copy, set_lead=set_lead,
	#	date=date)
	#check permissions
	perms = rdoc.get("jasper_roles")
	if not check_jasper_perm(perms, ptypes=["email"]):
		raise frappe.PermissionError((_("You are not allowed to send emails related to") + ": {doctype} {name}").format(
			doctype=data.get("doctype"), name=data.get('report_name')))

	sendmail(file_name, output, doctype=doctype, name=name, content=content, subject=subject, sent_or_received=sent_or_received,
		sender=sender, recipients=recipients, print_html=print_html, print_format=print_format, attachments=attachments,
		send_me_a_copy=send_me_a_copy)

	filepath = jasper_save_email(data, file_name, output, result[0].get("requestId"), sender)
	print "jasper email filepath {}".format(filepath)

	sender = get_sender(sender)
	set_jasper_email_doctype(data.get('report_name'), recipients, sender, frappe.utils.now(), filepath, file_name)
	#to get a report in another format to use in email
	#from jasperserver.core.exportDescriptor import ExportDescriptor
	#rr = ExportDescriptor()

"""
def jasper_make_attach(data, file_name, output, attachments, result):

	from frappe.utils.file_manager import get_site_path
	path_join = os.path.join
	#rdoc = frappe.get_doc(data.get("doctype"), data.get('report_name'))
	#for_all_sites = rdoc.jasper_all_sites_report
	#jasper_path = get_jasper_path(for_all_sites)
	public = get_site_path("public")
	jasper_path_intern = path_join("jasper_sent_email", result[0].get("requestId"))
	outputPath = path_join(public, jasper_path_intern)
	frappe.create_folder(outputPath)
	file_path = path_join(outputPath, file_name)
	file_path_intern = path_join(jasper_path_intern, file_name)
	write_StringIO_to_file(file_path, output)

	attach = json.loads(attachments)
	attach.append(file_path_intern)
	print "sent by email 2... {} attach {}".format(file_path_intern, attach)

	return json.dumps(attach)
"""

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
	print "get_jasper_email_report 3 {} {}".format(file_path, file_name)
	jsr = jasper_session_obj or Jr.JasperRoot()
	output = get_file(file_path, modes="rb")
	jsr.prepare_file_to_client(file_name, output)

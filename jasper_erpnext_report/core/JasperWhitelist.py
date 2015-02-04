from __future__ import unicode_literals
__author__ = 'luissaguas'
from frappe import _
import frappe
import json
from urllib2 import unquote
import logging

#import jasper_erpnext_report.utils.utils as utils
import JasperRoot as Jr
from jasper_erpnext_report import jasper_session_obj

_logger = logging.getLogger(frappe.__name__)


def boot_session(bootinfo):
	#bootinfo['jasper_server_info'] = get_server_info()
	bootinfo['jasper_reports_list'] = get_reports_list_for_all()


@frappe.whitelist()
def get_reports_list_for_all():
	jsr = jasper_session_obj or Jr.JasperRoot()
	return jsr.get_reports_list_for_all()

@frappe.whitelist()
def get_reports_list(doctype, docnames):
	jsr = jasper_session_obj or Jr.JasperRoot()
	return jsr.get_reports_list(doctype, docnames)


@frappe.whitelist()
def report_polling(data):
	jsr = jasper_session_obj or Jr.JasperRoot()
	return jsr.report_polling(data)


@frappe.whitelist()
def get_report(data):
	print "data get_reportssss {}".format(unquote(data))
	if not data:
		frappe.throw(_("No data for this Report!!!"))
	data = json.loads(unquote(data))
	jsr = jasper_session_obj or Jr.JasperRoot()
	jsr.get_report_server(data)


@frappe.whitelist()
def run_report(data, docdata=None, rtype="Form"):
	from frappe.utils import pprint_dict
	if not data:
		frappe.throw("No data for this Report!!!")
	data = json.loads(data)
	jsr = jasper_session_obj or Jr.JasperRoot()
	print "params in run_report {}".format(pprint_dict(data))
	return jsr.run_report(data, docdata=docdata, rtype=rtype)

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
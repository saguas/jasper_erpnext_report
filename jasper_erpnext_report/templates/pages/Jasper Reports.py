from __future__ import unicode_literals
__author__ = 'luissaguas'

import frappe, os, jasper_erpnext_report, re
from frappe import _
from jasper_erpnext_report.utils.file import get_file, get_extension
no_cache = True

def get_context(context):
	"""
	jasper_report_path = frappe.form_dict.jasper_doc_path
	module_path = os.path.normpath(os.path.join(os.path.dirname(jasper_erpnext_report.__file__), "public", "reports", frappe.local.site , jasper_report_path))
	content = get_file(module_path)
	path = jasper_report_path.rsplit("/",1)[0]
	assets_path = os.path.join("jasper_erpnext_report", "reports", frappe.local.site , path)#os.path.normpath()

	return {
		"jasper_report_path": scrub_urls(content, assets_path)
	}
	"""
	if frappe.local.session['sid'] == 'Guest':
		return {"message":_("Please login first!"), "title":_("Not Permitted")}

	jasper_report_path = frappe.form_dict.jasper_doc_path
	if not jasper_report_path:
		return {"message":_("Switch to Desk to see the list of reports."), "title":_("Not Permitted")}

	filename = jasper_report_path.rsplit("/",1)[1]

	ext = get_extension(filename)
	viewer = viewer_pdf if "pdf" in ext else viewer_html
	return viewer(filename)

def viewer_html(filename):
	jasper_report_path = frappe.form_dict.jasper_doc_path
	url = frappe.utils.get_url()
	if url.endswith("/"): url = url[:-1]
	url = url + "/assets/jasper_erpnext_report/reports/" + frappe.local.site + "/" + jasper_report_path
	url = frappe.utils.quote_urls(url)
	return {
		"jasper_report_path": url#"http://localhost:8000/assets/jasper_erpnext_report/pdfjs/web/viewer.html?file=Cherry.pdf"
	}

def viewer_pdf(filename):
	jasper_report_path = frappe.form_dict.jasper_doc_path
	#module_path = os.path.normpath(os.path.join(os.path.dirname(jasper_erpnext_report.__file__), "public", "viewer.html"))
	#content = get_file(module_path)
	#print "content viewer pdfjs {}".format(content)
	#assets_path = os.path.join("jasper_erpnext_report", "pdfjs")#os.path.normpath()
	url = frappe.utils.get_url()
	if url.endswith("/"): url = url[:-1]

	urlpdf = url + "/assets/jasper_erpnext_report/reports/"+ frappe.local.site + "/" + jasper_report_path
	url = frappe.utils.quote_urls(urlpdf)
	urlbase = frappe.utils.get_url() + "/assets/jasper_erpnext_report/pdfjs/web/viewer.html?file=" + url
	urlbase = frappe.utils.quote_urls(urlbase)
	return {
		"jasper_report_path": urlbase
	}

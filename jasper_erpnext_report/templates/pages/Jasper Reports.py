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
		return {"message":_("Please login first!"), "doc_title":_("Not Permitted")}

	jasper_report_path = frappe.form_dict.jasper_doc_path
	if not jasper_report_path:
		return {"message":_("Switch to Desk to see the list of reports."), "doc_title":_("Not Permitted")}

	filename = jasper_report_path.rsplit("/",1)[1]
	doc_title = jasper_report_path.split("/",1)[0]
	ext = get_extension(filename)
	#viewer = viewer_pdf if "pdf" in ext else viewer_html

	if "pdf" == ext:
		viewer = viewer_pdf
	elif "html" == ext:
		viewer = viewer_html
	else:
		return {"message":_("Switch to Desk to see the list of reports."), "doc_title":_("Not Permitted")}
	#viewer = viewer_pdf if "pdf" in ext else viewer_html

	user_email = frappe.db.get_value("User", frappe.session.user, "email")
	#sent_to = frappe.db.get_value("Jasper Email Report", frappe.session.user, "jasper_email_sent_to")
	crit = "`tabJasper Email Report`.jasper_email_sent_to='%s'" % (user_email,)
	context.children = frappe.get_all("Jasper Email Report", filters=[crit], fields=["jasper_report_path", "jasper_email_report_name", "jasper_file_name", "jasper_email_date"], order_by="jasper_email_date ASC", limit_page_length=10)
	context.pathname = "Jasper Reports?jasper_doc_path=" + jasper_report_path
	print "context pathname children {} jasper_report_path {}".format(context.pathname, context.children)
	return viewer(doc_title)


def viewer_html(filename):
	jasper_report_path = frappe.form_dict.jasper_doc_path
	url = frappe.utils.get_url()
	if url.endswith("/"): url = url[:-1]
	url = url + "/assets/jasper_erpnext_report/reports/" + frappe.local.site + "/" + jasper_report_path
	url = frappe.utils.quote_urls(url)
	return {
		"jasper_report_path": url,#"http://localhost:8000/assets/jasper_erpnext_report/pdfjs/web/viewer.html?file=Cherry.pdf"
		"doc_title": filename,
		"rtype":"html"
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
	#urlpdf = "/assets/jasper_erpnext_report/reports/"+ frappe.local.site + "/" + jasper_report_path
	url = frappe.utils.quote_urls(urlpdf)
	#urlbase = frappe.utils.get_url() + "/assets/jasper_erpnext_report/pdfjs/web/viewer.html?file=" + url
	urlbase = frappe.utils.quote_urls(url)
	return {
		"jasper_report_path": urlbase,
		"doc_title": filename,
		"rtype":"pdf"
	}

def Old_viewer_pdf(filename):
	jasper_report_path = frappe.form_dict.jasper_doc_path
	#module_path = os.path.normpath(os.path.join(os.path.dirname(jasper_erpnext_report.__file__), "public", "viewer.html"))
	#content = get_file(module_path)
	#print "content viewer pdfjs {}".format(content)
	#assets_path = os.path.join("jasper_erpnext_report", "pdfjs")#os.path.normpath()
	url = frappe.utils.get_url()
	if url.endswith("/"): url = url[:-1]

	urlpdf = url + "/assets/jasper_erpnext_report/reports/"+ frappe.local.site + "/" + jasper_report_path
	#urlpdf = "/assets/jasper_erpnext_report/reports/"+ frappe.local.site + "/" + jasper_report_path
	url = frappe.utils.quote_urls(urlpdf)
	urlbase = frappe.utils.get_url() + "/assets/jasper_erpnext_report/pdfjs/web/viewer.html?file=" + url
	#urlbase = frappe.utils.get_url() + "/assets/jasper_erpnext_report/ViewerJS/viewer.html#" + url
	urlbase = frappe.utils.quote_urls(urlbase)
	return {
		"jasper_report_path": urlbase,
		"doc_title": filename,
		"rtype":"pdf"
	}

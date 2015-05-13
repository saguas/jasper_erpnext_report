from __future__ import unicode_literals
__author__ = 'luissaguas'

import frappe
import frappe.utils
from frappe import _
from jasper_erpnext_report.utils.file import get_extension
no_cache = True

def get_context(context):
	if frappe.local.session['sid'] == 'Guest':
		return {"message":_("Please login first."), "doc_title":_("Not Permitted")}

	jasper_report_path = frappe.form_dict.jasper_doc_path
	if not jasper_report_path:
		return {"message":_("Switch to Desk to see the list of reports."), "doc_title":_("Not Permitted")}

	filename = jasper_report_path.rsplit("/",1)[1]
	doc_title = jasper_report_path.split("/",1)[0]
	ext = get_extension(filename)

	if "pdf" == ext:
		viewer = viewer_pdf
	elif "html" == ext:
		viewer = viewer_html
	else:
		return {"message":_("Switch to Desk to see the list of reports."), "doc_title":_("Not Permitted")}

	context.children = get_all_email_reports()
	context.pathname = "Jasper Reports?jasper_doc_path=" + jasper_report_path
	return viewer(doc_title)


def get_all_email_reports():
	approved_childs = []
	user_email = frappe.db.get_value("User", frappe.session.user, "email")
	crit = "`tabJasper Email Report`.jasper_email_sent_to='%s'" % (user_email,)
	childrens = frappe.get_all("Jasper Email Report", filters=[crit], fields=["jasper_report_path", "jasper_email_report_name", "jasper_file_name", "jasper_email_date"], order_by="jasper_email_date ASC", limit_page_length=10)
	for child in childrens:
		ext = get_extension(child.jasper_file_name)
		if ext == "pdf" or ext == "html":
			approved_childs.append(child)

	return approved_childs

def viewer_html(filename):
	jasper_report_path = frappe.form_dict.jasper_doc_path
	url = frappe.utils.get_url()
	if url.endswith("/"): url = url[:-1]
	url = url + "/assets/jasper_erpnext_report/reports/" + frappe.local.site + "/" + jasper_report_path
	url = frappe.utils.quote_urls(url)
	return {
		"jasper_report_path": url,
		"doc_title": filename,
		"rtype":"html"
	}

def viewer_pdf(filename):
	jasper_report_path = frappe.form_dict.jasper_doc_path
	url = frappe.utils.get_url()
	if url.endswith("/"): url = url[:-1]

	urlpdf = url + "/assets/jasper_erpnext_report/reports/"+ frappe.local.site + "/" + jasper_report_path
	url = frappe.utils.quote_urls(urlpdf)
	urlbase = frappe.utils.quote_urls(url)
	return {
		"jasper_report_path": urlbase,
		"doc_title": filename,
		"rtype":"pdf"
	}


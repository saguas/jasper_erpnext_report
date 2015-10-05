# Copyright (c) 2013, Luis Fernandes and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import os, json
from frappe import _
from frappe.model.document import Document
from jasper_erpnext_report.utils.file import get_image_name, JasperXmlReport,\
		get_jasper_path
from jasper_erpnext_report.utils.jasper_file_jrxml import check_root_exists, get_jrxml_root
from jasper_erpnext_report.utils.utils import check_queryString_param, jaspersession_set_value, jaspersession_get_value,\
	check_jasper_perm
from frappe.utils import cint
from jasper_erpnext_report.core.JasperRoot import JasperRoot
from jasper_erpnext_report.utils.cache import redis_transation

"""

HOOKS:
		on_jasper_params_ids(data=None, params=None);
		on_jasper_params(data=None, params=None);
		jasper_before_run_report(data=None, docdata=None);
"""


class JasperReports(Document):

	def on_update(self, method=None):


		#if we are importing docs from jasperserver
		if not frappe.flags.in_import:

			r_filters=["`tabJasper Reports`.jasper_doctype is NULL", "`tabJasper Reports`.report is NULL"]
			jr = JasperRoot()
			data = jr._get_reports_list(filters_report=r_filters)
			#report_list_dirt_doc is not called from here
			cached = redis_transation(data, "report_list_all")
			if cached and data:
				jaspersession_set_value("report_list_dirt_all", False)
				jaspersession_set_value("report_list_dirt_doc", True)
			elif data:
				#redis not cache
				jaspersession_set_value("report_list_dirt_doc", True)
				jaspersession_set_value("report_list_dirt_all", True)

			if check_root_exists(self.doctype, self.name):
				return
			#if jrxml file was removed then remove all associated images and params
			if self.jasper_report_origin.lower() == "localserver":
				frappe.db.sql("""delete from `tab%s` where %s=%s """ % ("Jasper Parameter", "parent", '%s'),(self.name), auto_commit=1)
				self.query = ""

	def before_save(self, method=None):
		self.jasper_doctype = None if not frappe.utils.strip(self.jasper_doctype) else self.jasper_doctype
		self.report = None if not frappe.utils.strip(self.report) else self.report
		if not self.jasper_param_message:
			self.jasper_param_message = frappe.db.get_values_from_single(["jasper_param_message"], None, "JasperServerConfig")[0][0].format(report=self.jasper_report_name, user=frappe.local.session['user'])

		#check if Jasper is configurated
		use_jasper_server = frappe.db.get_values_from_single(["use_jasper_server"], None, "JasperServerConfig")[0][0]
		if use_jasper_server == "None":
			frappe.throw(_("You need to configure Jasper first."))
			return

		print "before_save!!! "

		if check_root_exists(self.doctype, self.name):
			rootquery = ''
			self.query = ''
			jrxml_path = _get_jrxml_root_path(self)
			xmldoc = JasperXmlReport(jrxml_path)
			xmlname = check_if_xPath_exists(xmldoc)
			if xmlname and not check_for_report_xPath(xmldoc, xmlname, self):
				frappe.throw(_("Import %s for report %s first." % (xmlname + ".xml",self.jasper_report_name)))

			subreportquerys = getSubReportsQuery(xmldoc, self)
			subquery = ''
			for subreportquery in subreportquerys:
				subquery = subquery + subreportquery.get("name") + ":\n" + subreportquery.get("query") + "\n"

			if xmldoc.queryString or subquery:
				self.query =  xmldoc.name + ":\n" + xmldoc.queryString + "\n" + subquery
			#give feedback to the user shown related params
			params = xmldoc.get_params_from_xml()
			#get total number of parameters to concatenate with name of parameter
			is_copy = "Other"
			action_type = "Ask"

			for param in params:
				pname = param.xpath('./@name')
				pclass = param.xpath('./@class')
				ptype = pclass[0].split(".")
				c = len(ptype) - 1
				if check_param_exists(self, pname[0]):
					break
				if check_queryString_param(xmldoc.queryString, pname[0]):
					is_copy = "Is for where clause"
					action_type = "Automatic"
				self.append("jasper_parameters", {"__islocal": True, "jasper_param_name":pname[0], "jasper_param_type":ptype[c].lower().capitalize(),
						"jasper_param_action": action_type, "param_expression":"In", "is_copy":is_copy, "name": self.name + "_" + pname[0]})
			self.query = rootquery + self.query

			return
		#if jrxml file was removed then prepare to remove all associated images and params given feedback to the user
		if self.jasper_report_origin.lower() == "localserver":
			self.jasper_parameters = []
		return

	@property
	def jrxml_root_path(self):
		root_path = None
		docs = frappe.get_all("File", fields=["file_name", "file_url"], filters={"attached_to_name": self.name, "attached_to_doctype": self.doctype,
				"attached_to_report_name":"root"})
		try:
			root_path = docs[0].file_url
		except:
			frappe.msgprint(_("The report is missing."), raise_exception=True)

		return root_path


@frappe.whitelist()
def get_attachments(dn):
	if not dn:
		return
	attachments = []
	for f in frappe.db.sql("""select name, file_name, file_url, attached_to_report_name from
		`tabFile` where attached_to_name=%s and attached_to_doctype=%s""",
			(dn, "Jasper Reports"), as_dict=True):
		attachments.append({
			'name': f.name,
			'file_url': f.file_url,
			'file_name': f.file_name,
			'parent_report': f.attached_to_report_name
		})

	return attachments

def getSubReportsQuery(xmlroot, doc):
	subquery = []
	check_for_report_images(xmlroot, doc)
	jasper_path = get_jasper_path(doc.jasper_all_sites_report)
	subreports = xmlroot.subreports
	for path_name in subreports:
		report_path = path_name[:-7] + ".jrxml"
		file_path = frappe.utils.get_path(doc.name, report_path, base=jasper_path)
		try:
			xmldoc = JasperXmlReport(file_path)
			subquery.append({"name": xmldoc.name, "query": xmldoc.queryString})
			subquery.extend(xmldoc.datasets)
			#check if the subreport has subreports too
			subquery.extend(getSubReportsQuery(xmldoc, doc))
		except:
			frappe.msgprint(_("Subreport %s is missing." % (report_path)), raise_exception=True)

	return subquery

def check_for_report_images(xmldoc, doc):
	image_names_not_found = []
	report_images_count = 0
	images = xmldoc.get_images_from_xml()
	if not images:
		return
	parent = xmldoc.getProperty("jasperId")
	docs = frappe.get_all("File", fields=["file_name", "file_url"], filters={"attached_to_name": doc.name, "attached_to_doctype": doc.doctype,
						"attached_to_report_name":parent})

	for image in images:
		found = False
		try:
			fimage = json.loads(image.text)
		except:
			fimage = image.text

		report_image_name = get_image_name(fimage)
		for f in docs:
			list_img_name = f.file_url.split("compiled/",1)
			if len(list_img_name) > 1:
				img = list_img_name[1]
			else:
				img = list_img_name[0]

			if report_image_name == img:
				found = True
				report_images_count = report_images_count + 1
				break
		if not found:
			image_names_not_found.append(report_image_name)
	if not report_images_count == len(images):
		frappe.throw(_("Import %s image for report %s first." % (",".join(image_names_not_found),doc.jasper_report_name)))


def check_for_report_xPath(xmldoc, xmlname, doc):

	xmlname = xmlname + ".xml"
	parent = xmldoc.getProperty("jasperId")
	docs = frappe.get_all("File", fields=["file_name", "file_url"], filters={"attached_to_name": doc.name, "attached_to_doctype": doc.doctype,
						"attached_to_report_name":parent})
	for f in docs:
		list_file_name = f.file_url.split("compiled/",1)
		if len(list_file_name) > 1:
			file_name = list_file_name[1]
		else:
			file_name = list_file_name[0]
		if xmlname == file_name:
			return True

"""
Called from db_query.py method: def get_permission_query_conditions()
In this case is for check jasper permission on the documents to show to the client and the associated count
"""
def get_permission_query_conditions(user):
	if not user: user = frappe.local.session['user']
	if user=="Administrator":
		return ""
	if ignore_jasper_perm():
		return ""
	return """(exists(select * from `tabJasper PermRole` where `tabJasper PermRole`.parent=`tabJasper Reports`.`name` and
				`tabJasper PermRole`.jasper_role in ('%(roles)s') and `tabJasper PermRole`.jasper_can_read = 1))
		""" % {
			"roles": "', '".join([frappe.db.escape(r) for r in frappe.get_roles(user)])
		}


"""
Called from frappe.has_permission as controller
Verify which docs pass jasper permissions
"""
def has_jasper_permission(doc, ptype, user):
	perm = True
	if not ignore_jasper_perm():
		perm = check_jasper_perm(doc.jasper_roles, ptype, user)

	return perm

def ignore_jasper_perm():
	ignore_perm = jaspersession_get_value("jasper_ignore_perm_roles")
	if ignore_perm is None:
		ignore_perm = frappe.db.get_single_value("JasperServerConfig", "jasper_ignore_perm_roles")
		jaspersession_set_value("jasper_ignore_perm_roles", ignore_perm)

	if not cint(ignore_perm):
		return False

	return True

def _get_jrxml_root_path(doc):
	jasper_path = get_jasper_path(doc.jasper_all_sites_report)
	root_jrxml_name, root_jrxml_url = get_jrxml_root(doc.doctype, doc.name)
	file_path = os.path.join(jasper_path, doc.name, root_jrxml_name)
	return file_path

#jasper docs have the same params spread so don't let them repeat in doc parameter
def check_param_exists(doc, pname):
	exist = False
	idx_pname = pname.rfind(":")
	if idx_pname != -1:
		pname = pname[0:idx_pname]
	for p in doc.jasper_parameters:
		if p.jasper_param_name == pname:
			exist = True
			break
	return exist

def check_if_xPath_exists(xmldoc):
	return xmldoc.getProperty("XMLNAME")



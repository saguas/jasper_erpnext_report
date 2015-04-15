# Copyright (c) 2013, Luis Fernandes and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import os, json
from frappe import _
from frappe.model.document import Document
from jasper_erpnext_report.utils.file import delete_jrxml_images, get_image_name, JasperXmlReport,\
		get_jasper_path, check_root_exists, get_jrxml_root
from jasper_erpnext_report.utils.utils import check_queryString_param, jaspersession_set_value, jaspersession_get_value, check_jasper_perm
import logging
from frappe.utils import cint

_logger = logging.getLogger(frappe.__name__)


class JasperReports(Document):
	def on_update(self, method=None):
		jaspersession_set_value("report_list_dirt_all", True)
		jaspersession_set_value("report_list_dirt_doc", True)

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

		if check_root_exists(self.doctype, self.name):
			rootquery = ''
			self.query = ''
			jrxml_path = _get_jrxml_root_path(self)
			xmldoc = JasperXmlReport(jrxml_path)
			subreportquerys = getSubReportsQuery(xmldoc, self)
			subquery = ''
			for subreportquery in subreportquerys:
				subquery = subquery + subreportquery.get("name") + ":\n" + subreportquery.get("query") + "\n"

			if xmldoc.queryString or subquery:
				self.query =  xmldoc.name + ":\n" + xmldoc.queryString + "\n" + subquery
			#give feedback to the user shown related params
			params = xmldoc.get_params_from_xml()
			#get total number of parameters to concatenate with name of parameter
			idx = frappe.db.sql("""select count(*) from `tabJasper Parameter`""")[0][0] + 1
			is_copy = "Is for copies"
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
				self.append("jasper_parameters", {"__islocal": True, "jasper_param_name":pname[0], "jasper_param_type":ptype[c].lower().capitalize(),\
						"jasper_param_action": action_type, "param_expression":"In", "is_copy":is_copy, "name":pname[0] + ":" + str(idx)})
				idx = idx + 1
			self.query = rootquery + self.query
			return
		#if jrxml file was removed then prepare to remove all associated images and params given feedback to the user
		if self.jasper_report_origin.lower() == "localserver":
			self.jasper_parameters = []
			self.jasper_report_images = []
		return

	def on_trash(self, method=None):
		pass

	def on_jasper_params_ids(self, data=[], params=[]):
		print "new params hooks {} name {}".format(data, self.name)
		"""
		for param in params:
			if param.get('name') != "name_ids":
				pname = param.get("name")
				attrs = param.get("attrs")
				default_value = param.get("value")
				print "jasper_params hook: doc {0} data {1} pname {2} param {3} default_value {4}".format(self, data, pname, attrs.param_expression, default_value)
				a = ["'%s'" % t for t in default_value]
				value = "where name %s (%s)" % (attrs.param_expression, ",".join(a))
				if not default_value:
					default_value.append(value)
				else:
					param['value'] = value
				print "old_value {0} {1}".format(default_value, param.get('value'))
			else:
				param['value'].append('Administrator')
		"""
		ret = {"ids": ["Administrator", "luisfmfernandes@gmail.com"], "report_type": "List"}

		return ret

	def on_jasper_params(self, data=[], params=[]):
		a = []
		#for param in params:
			#a.append({"name":param.get("name"), "value": ["Administrator", "luisfmfernandes@gmail.com"], "param_type": _("is for where clause")})
		#a.append({"name": params[0].get("name"), "value":'select name, email from tabUser where name in ("luisfmfernandes@gmail.com")'})
		#a.append({"name": params[0].get("name"), "value":['Administrator', 'Guest'], "param_type": _("is for where clause")})
		a.append({"name": params[0].get("name"), "value":['Administrator', 'Guest'], "param_type": "is for where clause"})
		#a.append({"name": params[0].get("name"), "value":345})
		return a

	@property
	def jrxml_root_path(self):
		docs = frappe.get_all("File Data", fields=["file_name", "file_url"], filters={"attached_to_name": self.name, "attached_to_doctype": self.doctype,\
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
		`tabFile Data` where attached_to_name=%s and attached_to_doctype=%s""",
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
		report_path = path_name.split("/",1)[1][:-6] + "jrxml"
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
	docs = frappe.get_all("File Data", fields=["file_name", "file_url"], filters={"attached_to_name": doc.name, "attached_to_doctype": doc.doctype,\
						"attached_to_report_name":parent})

	for image in images:
		found = False
		try:
			fimage = json.loads(image.text)
		except:
			fimage = image.text

		report_image_name = get_image_name(fimage)
		for img in docs:
			if report_image_name == img.file_url.split("compiled/",1)[1]:
				found = True
				report_images_count = report_images_count + 1
				break
		if not found:
			image_names_not_found.append(report_image_name)
	if not report_images_count == len(images):
		frappe.throw(_("Import %s image for report %s first." % (",".join(image_names_not_found),doc.jasper_report_name)))

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


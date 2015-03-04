# Copyright (c) 2013, Luis Fernandes and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import os
from frappe import _
from frappe.model.document import Document
from jasper_erpnext_report.utils.file import get_jasper_path, get_jrxml_path, delete_jrxml_images, get_params, get_query, get_images, get_image_name,\
		remove_directory, get_jasper_path, get_compiled_path
from jasper_erpnext_report.utils.utils import check_queryString_param, jaspersession_set_value
import logging

_logger = logging.getLogger(frappe.__name__)


class JasperReports(Document):
	def on_update(self, method=None):
		jaspersession_set_value("report_list_dirt_all", True)
		jaspersession_set_value("report_list_dirt_doc", True)
		if self.jasper_upload_jrxml:
			return
		#if jrxml file was removed then remove all associated images and params
		if self.jasper_report_origin.lower() == "localserver":
			frappe.db.sql("""delete from `tab%s` where %s=%s """ % ("Jasper Parameter", "parent", '%s'),(self.name), auto_commit=1)
			#frappe.db.sql("""delete from `tab%s` where %s=%s """ % ("Jasper PermRole", "parent", '%s'),(self.name), auto_commit=1)
			delete_jrxml_images(self.doctype, self.name, self.jasper_all_sites_report)
			self.query = ""


	def before_save(self, method=None):
		if not self.jasper_param_message:
			self.jasper_param_message = frappe.db.get_values_from_single(["jasper_param_message"], None, "JasperServerConfig")[0][0].format(report=self.jasper_report_name, user=frappe.local.session['user'])
		if self.jasper_upload_jrxml:
			#give feedback to the user shown related params
			images = get_images_from_xml(self)
			img = check_for_images(self, images)
			if not img[0]:
				frappe.throw(_("Import %s image(s) for report %s first!!!" % (",".join(img[1]),self.jasper_report_name)))
			query = get_query_from_xml(self)
			for q in query:
				print "query**************** {}".format(q.text)
				if q.text:
					self.query = q.text
			params = get_params_from_xml(self)
			#get total number of parameters to concatenate with name of parameter
			idx = frappe.db.sql("""select count(*) from `tabJasper Parameter`""")[0][0] + 1
			is_copy = "Is for copies"
			action_type = "Ask"
			for param in params:
				pname = param.xpath('./@name')
				pclass = param.xpath('./@class')
				print "params: {0} pclass {1}".format(pname, pclass)
				ptype = pclass[0].split(".")
				c = len(ptype) - 1
				if check_param_exists(self, pname[0]):
					break
				if check_queryString_param(query, pname[0]):
					is_copy = "Is for where clause"
					action_type = "Automatic"
				self.append("jasper_parameters", {"__islocal": True, "jasper_param_name":pname[0], "jasper_param_type":ptype[c].lower().capitalize(),\
						"jasper_param_action": action_type, "param_expression":"In", "is_copy":is_copy, "name":pname[0] + ":" + str(idx)})
				_logger.info("jasperjrxml upload in update_old: {}".format(self.jasper_parameters))
				idx = idx + 1
			return
		#if jrxml file was removed then prepare to remove all associated images and params given feedback to the user
		if self.jasper_report_origin.lower() == "localserver":
			self.jasper_parameters = []
			self.jasper_report_images = []
		return

	def on_trash(self, method=None):
		jasper_path = get_jasper_path(self.jasper_all_sites_report)
		compiled_path = get_compiled_path(jasper_path, self.name)
		parent_path = os.path.normpath(os.path.join(compiled_path,".."))
		remove_directory(parent_path)

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
		print "new params hooks {} name {}".format(data, self.name)
		a = []
		for param in params:
			a.append({"name":param.get("name"), "value": ["Administrator", "luisfmfernandes@gmail.com"], "param_type": _("is for where clause")})
		return a

def _get_jrxml_path(doc):
	jasper_path = get_jasper_path(doc.jasper_all_sites_report)
	jrxml_path = get_jrxml_path(jasper_path, doc.jasper_upload_jrxml[1:])
	print "on_update called all sites? {0} jrxml_path {1}".format(doc.jasper_all_sites_report, jrxml_path)
	return jrxml_path

def get_params_from_xml(doc):
	jrxml_path = _get_jrxml_path(doc)
	return get_params(jrxml_path)

def get_query_from_xml(doc):
	jrxml_path = _get_jrxml_path(doc)
	return get_query(jrxml_path)

def get_images_from_xml(doc):
	jrxml_path = _get_jrxml_path(doc)
	return get_images(jrxml_path)

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

def check_for_images(doc, images):
	report_images_count = 0
	image_names_not_found = []
	for image in images:
		found = False
		report_image_name = get_image_name(image.text)
		print "report_image_name {}".format(report_image_name)
		for doc_image_path in doc.jasper_report_images:
			image_name = get_image_name(doc_image_path.jasper_report_image)
			print "doc_image_name {}".format(image_name)
			if report_image_name == image_name:
				report_images_count = report_images_count + 1
				found = True
				break
		if not found:
			image_names_not_found.append(report_image_name)
	return report_images_count == len(images), image_names_not_found

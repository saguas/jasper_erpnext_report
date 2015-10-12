from __future__ import unicode_literals
__author__ = 'luissaguas'

import frappe
from frappe import _
import os
from io import BytesIO
from jasper_erpnext_report.jasper_reports.compile_reports import jasper_compile
from jasper_erpnext_report.utils.file import check_extension, get_jasper_path, get_extension, JasperXmlReport,\
	write_file
from frappe.utils.file_manager import check_max_file_size, get_content_hash


class WriteFileJrxml(object):
	def __init__(self, dt, fname, content, parent):
		self.file_path = None
		self.dt = dt
		self.fname = fname
		self.content = content
		self.parent = parent
		self.dn = frappe.form_dict.docname
		self.autofilename = None
		self.ext = check_extension(self.fname)
		self.jasper_all_sites_report = frappe.db.get_value(self.dt, self.dn, 'jasper_all_sites_report')
		self.jasper_path = get_jasper_path(self.jasper_all_sites_report)
		self.compiled_path = get_compiled_path(self.jasper_path, self.dn)
		self.path_join = os.path.join
		self.scriptlet = None
		self.save_path = None
		self.subreport = False


	def get_original_query(self):
		import re
		queryString = re.search("<queryString>(.*?)</queryString>", self.content, re.S | re.M)
		if queryString:
			self.queryString = queryString.group(1)
			print "queryString Report %s" % self.queryString

	def insert_report_doc(self, dn=None):
		file_data = {}
		file_size = check_max_file_size(self.content)
		content_hash = get_content_hash(self.content)

		file_data.update({
			"doctype": "File",
			"attached_to_report_name": self.parent,
			"attached_to_doctype": self.dt,
			"attached_to_name": dn,
			"file_size": file_size,
			"content_hash": content_hash,
			'file_name': os.path.basename(self.rel_path),
			'file_url': os.sep + self.rel_path.replace('\\','/'),
		})

		f = frappe.get_doc(file_data)
		try:
			f.insert(ignore_permissions=True)
			if self.ext == "jrxml":
				self.make_content_jrxml(f.name)

		except frappe.DuplicateEntryError:
			return frappe.get_doc("File", f.duplicate_entry)
		return f

	def process(self, dn=None):

		print "process report dn %s" % dn
		if self.ext != "jrxml":
			self.process_childs()
		else:
			self.get_original_query()
			self.process_jrxmls()

		self.rel_path = os.path.relpath(self.file_path, self.jasper_path)

		f = self.insert_report_doc(dn=dn)

		try:
			self.save()

			if self.ext == "jrxml":
				self.compile()
		except Exception, e:
			frappe.delete_doc("File", f.name)
			print "Remove this doc: doctype {} docname {} error: {}".format(f.doctype, f.name, e)

		return f

	def process_childs(self):
		docs = frappe.get_all("File", fields=["file_name", "file_url"], filters={"attached_to_name": self.dn, "attached_to_doctype": self.dt, "name": self.parent})
		if not docs:
			frappe.msgprint(_("Add a report first."), raise_exception=True)
		for doc in docs:
			jrxml_ext = get_extension(doc.file_name)
			if jrxml_ext == "jrxml":
				jrxml_os_path = self.path_join(self.jasper_path, doc.file_url[1:])
				xmldoc = JasperXmlReport(jrxml_os_path)
				if (self.ext!="properties" and self.ext != "xml"):
					image_path = xmldoc.get_image_path_from_jrxml(self.fname)
					self.file_path= self.path_join(self.compiled_path, os.path.normpath(image_path))
				elif (self.ext == "xml"):
					xmlname = xmldoc.getProperty("XMLNAME")
					if xmlname:
						xname = xmlname + ".xml"
						if xname != self.fname:
							frappe.msgprint(_("This report does't have %s as file source." % (self.fname,)),raise_exception=True)
						self.file_path = self.path_join(self.compiled_path, os.path.normpath(self.fname))
					else:
						frappe.msgprint(_("This report does't have %s as file source." % (self.fname,)),raise_exception=True)
				else:
					value = xmldoc.get_attrib("resourceBundle")
					if not value or value not in self.fname:
						frappe.msgprint(_("This report does't have %s as properties." % (self.fname,)),raise_exception=True)
					self.file_path = self.path_join(self.compiled_path, os.path.normpath(self.fname))
				break
			else:
				frappe.msgprint(_("Add a file for this report first."),raise_exception=True)


	def process_jrxmls(self):
		rname = check_if_jrxml_exists_db(self.dt, self.dn, self.fname, self.parent)
		if rname:
			if rname:
				frappe.msgprint(_("Remove first the file (%s) associated with this document or (%s) is a wrong parent." % (rname, rname)),
					raise_exception=True)

		jrxml_path = get_jrxml_path(self.jasper_path, self.dn)
		self.file_path = self.path_join(jrxml_path, self.fname)

		#check if the parent has this jrxml as child
		docs = frappe.get_all("File", fields=["file_name", "file_url"], filters={"attached_to_name": self.dn, "attached_to_doctype": self.dt, "name": self.parent})
		if docs:
			xmldoc = JasperXmlReport(self.path_join(jrxml_path, docs[0].file_name))
			for sub in xmldoc.subreports:
				s = sub.rsplit("/",1)
				if len(s) > 1:
					if not (s[1][:-7] == self.fname[:-6]):
						frappe.msgprint(_("The report %s is not a subreport of %s."  % (self.fname[:-6], docs[0].file_name[:-6])),raise_exception=True)
				elif not (sub[:-7] == self.fname[:-6]):
					frappe.msgprint(_("The report %s is not a subreport of %s."  % (self.fname[:-6], docs[0].file_name[:-6])),raise_exception=True)

			if not xmldoc.subreports:
				frappe.msgprint(_("The report %s is not a subreport of %s."  % (self.fname[:-6], docs[0].file_name[:-6])),raise_exception=True)

			#self.subreport = True
			#self.file_path = self.path_join(jrxml_path, docs[0].file_name)

	def make_content_jrxml(self, name):
		import re

		xmldoc = JasperXmlReport(BytesIO(self.content))
		xmldoc.change_subreport_expression_path()
		self.scriptlet = xmldoc.get_attrib("scriptletClass")
		#TODO
		if not self.scriptlet:
			pass

		xmldoc.change_path_images()
		xmldoc.setProperty("parent", self.parent)
		xmldoc.setProperty("jasperId", name)

		self.content = xmldoc.toString()
		self.content = re.sub("<queryString>(.*?)</queryString>", "<queryString>%s</queryString>" % self.queryString, self.content, count=1, flags=re.S|re.M)

	def save(self):
		self.save_path = write_file(self.content, self.file_path)

	def compile(self):
		jasper_compile_jrxml(self.fname, self.file_path, self.compiled_path)


def get_compiled_path(dir_path, dn):
	jrxml_path = get_jrxml_path(dir_path, dn)
	compiled_path = frappe.utils.get_path("compiled", base=jrxml_path)
	frappe.create_folder(compiled_path)
	return compiled_path


def get_jrxml_path(dir_path, dn):
	jrxml_path = frappe.utils.get_path(dn, base=dir_path)
	return jrxml_path


def jasper_compile_jrxml(fname, file_path, compiled_path):
	c = len(fname) - 6
	jasper_compile(file_path, os.path.join(compiled_path, fname[:c] + ".jasper"))


def check_if_jrxml_exists_db(dt, dn, fname, parent=None):

	docs = frappe.get_all("File", fields=["file_name"], filters={"attached_to_name": dn, "attached_to_doctype": dt, "name": parent})
	for doc in docs:
		jrxml_ext = get_extension(doc.file_name)
		if not (jrxml_ext == "jrxml"):
			return doc.file_name
		return doc.file_name if fname == doc.file_name else None
	return None

def check_root_exists(dt, dn):
	docs = frappe.get_all("File", fields=["file_name"], filters={"attached_to_name": dn, "attached_to_doctype": dt, "attached_to_report_name": "root"})
	return len(docs) > 0


def get_jrxml_root(dt,dn):
	furl = None
	fname = None
	docs = frappe.get_all("File", fields=["file_name", "file_url"], filters={"attached_to_name": dn, "attached_to_doctype": dt, "attached_to_report_name": "root"})
	if docs:
		fname = docs[0].file_name
		furl = docs[0].file_url
	return fname, furl


def delete_file_jrxml(doc, event):
	dt = doc.attached_to_doctype
	if dt == "Jasper Reports":
		dn = doc.attached_to_name
		ext = get_extension(doc.file_name)
		jasper_all_sites_report = frappe.db.get_value(dt, dn, 'jasper_all_sites_report')
		file_path = os.path.join(get_jasper_path(jasper_all_sites_report), doc.file_url[1:])
		path = os.path.normpath(os.path.join(file_path,".."))

		#don't remove directory if it is a subreport
		if ext == "jrxml":
			file_root_name, file_root_url = get_jrxml_root(dt,dn)
			if file_root_url == doc.file_url:
				from .file import remove_directory
				remove_directory(path)
				frappe.db.sql("""delete from `tab%s` where %s=%s """ % ("Jasper Parameter", "parent", '%s'),(dn), auto_commit=1)
				frappe.db.set_value(dt, dn, 'query', "")
		else:
			delete_jrxml_child_file(doc.file_url, jasper_all_sites_report)


def delete_file_jrxml_old(doc, event):
	dt = doc.attached_to_doctype
	if dt == "Jasper Reports":
		dn = doc.attached_to_name
		ext = get_extension(doc.file_name)
		jasper_all_sites_report = frappe.db.get_value(dt, dn, 'jasper_all_sites_report')
		file_path = os.path.join(get_jasper_path(jasper_all_sites_report), doc.file_url[1:])
		if os.path.exists(file_path) and ext == "jrxml":
			os.remove(file_path)
			delete_jrxml_images(dt, dn, jasper_all_sites_report)
			frappe.db.sql("""delete from `tab%s` where %s=%s """ % ("Jasper Parameter", "parent", '%s'),(dn), auto_commit=1)
			frappe.db.set_value(dt, dn, 'query', "")
		else:
			delete_jrxml_child_file(dt, jasper_all_sites_report)


def delete_jrxml_child_file(path, jasper_all_sites):
	file_path = os.path.join(get_jasper_path(jasper_all_sites),path[1:])
	if os.path.exists(file_path):
		os.remove(file_path)

#delete all images associated to jrxml file
def delete_jrxml_images(dt, dn, jasper_all_sites = False):
	images = frappe.get_all("File", fields=["file_url"], filters={"attached_to_name": dn, "attached_to_doctype": dt})
	for image in images:
		file_path = image.get('file_url')
		ext = check_extension(file_path)
		if ext != "jrxml":
			delete_jrxml_child_file(dt, jasper_all_sites)

def write_file_jrxml(fname, content, dn=None, content_type=None, parent=None):
	dt = frappe.form_dict.doctype
	if dt == "Jasper Reports":
		wobj = WriteFileJrxml(dt, fname, content, parent)
		f = wobj.process(dn=dn)

		return f
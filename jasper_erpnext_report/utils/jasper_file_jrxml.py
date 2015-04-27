from __future__ import unicode_literals
__author__ = 'luissaguas'

import frappe
from frappe import _
import os
from io import BytesIO
from jasper_erpnext_report.jasper_reports.compile_reports import jasper_compile
from frappe.utils.file_manager import delete_file_from_filesystem
from jasper_erpnext_report.utils.file import check_extension, get_jasper_path, get_extension, JasperXmlReport,\
	write_file


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


	def process(self):

		if self.ext != "jrxml":
			self.process_childs()
		else:
			self.process_jrxmls()

		self.save()

		if self.ext == "jrxml":
			self.compile()

		self.rel_path = os.path.relpath(self.save_path, self.jasper_path)

		return self.rel_path

	def process_childs(self):
		docs = frappe.get_all("File Data", fields=["file_name", "file_url"], filters={"attached_to_name": self.dn, "attached_to_doctype": self.dt, "name": self.parent})
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
		if rname or check_root_exists(self.dt, self.dn):
			frappe.msgprint(_("Remove first the file (%s) associated with this document or (%s) is a wrong parent." % (rname, rname)),
				raise_exception=True)
		jrxml_path = get_jrxml_path(self.jasper_path, self.dn)
		self.file_path = self.path_join(jrxml_path, self.fname)

		#check if the parent has this jrxml as child
		docs = frappe.get_all("File Data", fields=["file_name", "file_url"], filters={"attached_to_name": self.dn, "attached_to_doctype": self.dt, "name": self.parent})
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

		xmldoc = JasperXmlReport(BytesIO(self.content))
		xmldoc.change_subreport_expression_path()
		self.scriptlet = xmldoc.get_attrib("scriptletClass")
		#TODO
		if not self.scriptlet:
			pass

		xmldoc.change_path_images()
		xmldoc.setProperty("parent", self.parent)
		self.autofilename = frappe.model.naming.make_autoname("File.#####", doctype='')
		xmldoc.setProperty("jasperId", self.autofilename)

		self.content = xmldoc.toString()

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

	docs = frappe.get_all("File Data", fields=["file_name"], filters={"attached_to_name": dn, "attached_to_doctype": dt, "name": parent})
	for doc in docs:
		jrxml_ext = get_extension(doc.file_name)
		if not (jrxml_ext == "jrxml"):
			return doc.file_name
		return doc.file_name if fname == doc.file_name else None
	return None

def check_root_exists(dt, dn):
	docs = frappe.get_all("File Data", fields=["file_name"], filters={"attached_to_name": dn, "attached_to_doctype": dt, "attached_to_report_name": "root"})
	return len(docs) > 0


def get_jrxml_root(dt,dn):
	docs = frappe.get_all("File Data", fields=["file_name", "file_url"], filters={"attached_to_name": dn, "attached_to_doctype": dt, "attached_to_report_name": "root"})
	return docs[0].file_name, docs[0].file_url


def delete_file_jrxml(doc, event):
	dt = doc.attached_to_doctype
	if dt == "Jasper Reports":
		dn = doc.attached_to_name
		ext = get_extension(doc.file_name)
		jasper_all_sites_report = frappe.db.get_value(dt, dn, 'jasper_all_sites_report')
		file_path = os.path.join(get_jasper_path(jasper_all_sites_report), doc.file_url[1:])
		path = os.path.normpath(os.path.join(file_path,".."))
		file_root_name, file_root_url = get_jrxml_root(dt,dn)

		#don't remove directory if it is a subreport
		if ext == "jrxml" and file_root_url == doc.file_url:
			from . file import remove_directory
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
	print "file_path {}".format(file_path)
	if os.path.exists(file_path):
		os.remove(file_path)

#delete all images associated to jrxml file
def delete_jrxml_images(dt, dn, jasper_all_sites = False):
	images = frappe.get_all("File Data", fields=["file_url"], filters={"attached_to_name": dn, "attached_to_doctype": dt})
	for image in images:
		file_path = image.get('file_url')
		ext = check_extension(file_path)
		if ext != "jrxml":
			delete_jrxml_child_file(dt, jasper_all_sites)

"""
def get_next_hook_method(hook_name, last_method_name, fallback=None):
	method = (frappe.get_hooks().get(hook_name))
	if method:
		try:
			method = frappe.get_attr(method[method.index(last_method_name) + 1])
			return method
		except:
			return fallback
"""

def write_file_jrxml(fname, content, content_type=None, parent=None):
	#path_join = os.path.join
	#file_path = None
	dt = frappe.form_dict.doctype
	if dt == "Jasper Reports":
		from . jasper_file_jrxml import WriteFileJrxml
		wobj = WriteFileJrxml(dt, fname, content, parent)
		"""
		autofilename = None
		ext = check_extension(fname)
		dn = frappe.form_dict.docname
		jasper_all_sites_report = frappe.db.get_value(dt, dn, 'jasper_all_sites_report')
		jasper_path = get_jasper_path(jasper_all_sites_report)
		compiled_path = get_compiled_path(jasper_path, dn)
		if ext != "jrxml":
			docs = frappe.get_all("File Data", fields=["file_name", "file_url"], filters={"attached_to_name": dn, "attached_to_doctype": dt, "name": parent})
			if not docs:
				frappe.msgprint(_("Add a report first."), raise_exception=True)
			for doc in docs:
				jrxml_ext = get_extension(doc.file_name)
				if jrxml_ext == "jrxml":
					jrxml_os_path = path_join(jasper_path, doc.file_url[1:])
					xmldoc = JasperXmlReport(jrxml_os_path)
					if (ext!="properties" and ext != "xml"):
						image_path = xmldoc.get_image_path_from_jrxml(fname)
						file_path= path_join(compiled_path, os.path.normpath(image_path))
					elif (ext == "xml"):
						xmlname = xmldoc.getProperty("XMLNAME")
						if xmlname:
							xname = xmlname + ".xml"
							if xname != fname:
								frappe.msgprint(_("This report does't have %s as file source." % (fname,)),raise_exception=True)
							file_path = path_join(compiled_path, os.path.normpath(fname))
						else:
							frappe.msgprint(_("This report does't have %s as file source." % (fname,)),raise_exception=True)
					else:
						value = xmldoc.get_attrib("resourceBundle")
						if not value or value not in fname:
							frappe.msgprint(_("This report does't have %s as properties." % (fname,)),raise_exception=True)
						file_path= path_join(compiled_path, os.path.normpath(fname))
					break
				else:
					frappe.msgprint(_("Add a file for this report first."),raise_exception=True)
		else:
			rname = check_if_jrxml_exists_db(dt, dn, fname, parent)
			if rname or check_root_exists(dt,dn):
				frappe.msgprint(_("Remove first the file (%s) associated with this document or (%s) is a wrong parent." % (rname, rname)),
					raise_exception=True)
			jrxml_path = get_jrxml_path(jasper_path, dn)
			file_path = path_join(jrxml_path, fname)

			#check if the parent has this jrxml as child
			docs = frappe.get_all("File Data", fields=["file_name", "file_url"], filters={"attached_to_name": dn, "attached_to_doctype": dt, "name": parent})
			if docs:
				xmldoc = JasperXmlReport(path_join(jrxml_path, docs[0].file_name))
				for sub in xmldoc.subreports:
					s = sub.rsplit("/",1)
					if len(s) > 1:
						if not (s[1][:-7] == fname[:-6]):
							frappe.msgprint(_("The report %s is not a subreport of %s."  % (fname[:-6], docs[0].file_name[:-6])),raise_exception=True)
					elif not (sub[:-7] == fname[:-6]):
						frappe.msgprint(_("The report %s is not a subreport of %s."  % (fname[:-6], docs[0].file_name[:-6])),raise_exception=True)
				else:
					frappe.msgprint(_("The report %s is not a subreport of %s."  % (fname[:-6], docs[0].file_name[:-6])),raise_exception=True)

			xmldoc = JasperXmlReport(BytesIO(content))
			xmldoc.change_subreport_expression_path()
			scriptlet = xmldoc.get_attrib("scriptletClass")
			#TODO
			if not scriptlet:
				pass

			xmldoc.change_path_images()
			xmldoc.setProperty("parent", parent)
			autofilename = frappe.model.naming.make_autoname("File.#####", doctype='')
			xmldoc.setProperty("jasperId", autofilename)

			content = xmldoc.toString()
		"""
		path = wobj.process()
		#fpath = write_file(wobj.content, wobj.file_path)
		#path =  os.path.relpath(fpath, wobj.jasper_path)
		#if wobj.ext == "jrxml":
		#	jasper_compile_jrxml(wobj.fname, wobj.file_path, wobj.compiled_path)

		return {
			'name': wobj.autofilename or None,
			'file_name': os.path.basename(path),
			'file_url': os.sep + path.replace('\\','/'),
			"content": wobj.content
		}
	#else:
	#	return save_file_on_filesystem(fname, content, content_type)

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
import StringIO
from PIL import Image, ImageOps


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

	def insert_report_doc(self, dn=None):
		file_data = {}
		file_size = check_max_file_size(self.content)
		content_hash = get_content_hash(self.content)


		file_name = os.path.basename(self.rel_path)
		image = False

		file_url = os.sep + self.rel_path.replace('\\','/')
		try:
			Image.open(StringIO.StringIO(self.content)).verify()
			file_url = os.sep + "files" + os.sep + self.rel_path.replace('\\','/')
			image = True
		except Exception:
			pass


		file_data.update({
			"doctype": "File",
			"attached_to_report_name": self.parent,
			"attached_to_doctype": self.dt,
			"attached_to_name": dn,
			"file_size": file_size,
			"content_hash": content_hash,
			'file_name': file_name,
			'file_url': file_url,
		})

		f = frappe.get_doc(file_data)
		f.flags.ignore_file_validate = True
		if image:
			self.make_thumbnail(file_url, f, dn)

		under = "Home/Attachments"
		f.folder = under + os.path.dirname(file_url.replace("/files", ""))
		self.create_new_folder(file_url, dn)

		try:
			f.insert(ignore_permissions=True)
			if self.ext == "jrxml":
				self.make_content_jrxml(f.name)
		except frappe.DuplicateEntryError:
			return frappe.get_doc("File", f.duplicate_entry)
		return f

	def process(self, dn=None):

		if self.ext != "jrxml":
			self.process_childs()
		else:
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
				#jrxml_os_path = self.path_join(self.jasper_path, doc.file_url[1:])
				jrxml_os_path = self.path_join(self.jasper_path, get_file_path(doc.file_url))
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
		#import re
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
		#self.content = re.sub("<queryString>(.*?)</queryString>", "<queryString>%s</queryString>" % self.queryString, self.content, count=1, flags=re.S|re.M)

	def save(self):
		self.save_path = write_file(self.content, self.file_path)

	def compile(self):
		jasper_compile_jrxml(self.fname, self.file_path, self.compiled_path)

	def make_thumbnail(self, file_url, doc, dn):
		try:
			image = Image.open(StringIO.StringIO(self.content))
			filename, extn = file_url.rsplit(".", 1)
		except IOError:
				frappe.msgprint("Unable to read file format for {0}".format(os.path.realpath(self.file_path)))
				return

		thumbnail = ImageOps.fit(
			image,
			(300, 300),
			Image.ANTIALIAS
		)

		thumbnail_url = filename + "." + extn

		path = os.path.abspath(frappe.get_site_path("public", thumbnail_url.lstrip("/")))

		frappe.create_folder(os.path.dirname(path))

		try:
			thumbnail.save(path)
			doc.db_set("thumbnail_url", thumbnail_url)
		except IOError:
			frappe.msgprint("Unable to write file format for {0}".format(path))

	def create_new_folder(self, file_url, dn):
		""" create new folder under current parent folder """

		if not file_url.startswith("/files/"):
			file_url = "/files" + file_url
		filename, extn = file_url.rsplit(".", 1)

		thumbnail_url = filename + "." + extn

		under = "Home/Attachments"
		for file_name in os.path.dirname(thumbnail_url.replace("/files/", "")).split("/"):
			try:
				folder = under + "/" + file_name
				print "new folder is 3 %s thumbnail %s file_name %s" % (folder, thumbnail_url, file_name)
				file = frappe.db.sql("""select name from `tabFile`
				where name=%s""", (folder,))
				if not file:
					file = frappe.new_doc("File")
					file.file_name = file_name
					file.is_folder = 1
					file.folder = under
					file.attached_to_doctype = self.dt
					file.attached_to_name =  dn
					file.insert()
				under = under + "/" + file_name
			except:
				pass


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
	print "delete file_name %s attach to doctype %s attech to name %s" % (doc.file_name, doc.attached_to_doctype, doc.attached_to_name)
	dt = doc.attached_to_doctype
	if dt == "Jasper Reports":
		if doc.is_folder:
			import shutil
			under = "Home/Attachments"
			parent_folder = os.path.join(doc.folder, doc.file_name)
			rel_path = os.path.relpath(parent_folder, under)
			path = os.path.abspath(frappe.get_site_path("public", "files", rel_path))
			print "removing directory %s" % path
			try:
				#os.remove(path)
				shutil.rmtree(path)
				return True
			except Exception, e:
				frappe.throw("Error: %s" % e)

		else:
			dn = doc.attached_to_name
			ext = get_extension(doc.file_name)
			jasper_all_sites_report = frappe.db.get_value(dt, dn, 'jasper_all_sites_report')
			#file_path = os.path.join(get_jasper_path(jasper_all_sites_report), doc.file_url[1:])
			file_path = os.path.join(get_jasper_path(jasper_all_sites_report), get_file_path(doc.file_url))
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
				#delete_jrxml_child_file(doc.file_url.split("/files")[-1], jasper_all_sites_report)
				delete_jrxml_child_file(get_file_path(doc.file_url), jasper_all_sites_report)

"""
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
			frappe.db.sql("delete from `tab%s` where %s=%s " % ("Jasper Parameter", "parent", '%s'),(dn), auto_commit=1)
			frappe.db.set_value(dt, dn, 'query', "")
		else:
			delete_jrxml_child_file(dt, jasper_all_sites_report)
"""

def delete_jrxml_child_file(path, jasper_all_sites):
	filename, extn = path.rsplit(".", 1)
	thumbnail_url = filename + "." + extn
	ppath = os.path.abspath(frappe.get_site_path("public", "files", thumbnail_url.lstrip("/")))
	if os.path.exists(ppath):
		os.remove(ppath)

	file_path = os.path.join(get_jasper_path(jasper_all_sites),path)
	if os.path.exists(file_path):
		os.remove(file_path)

#delete all images associated to jrxml file
def delete_jrxml_images(dt, dn, jasper_all_sites = False):
	images = frappe.get_all("File", fields=["file_url"], filters={"attached_to_name": dn, "attached_to_doctype": dt})
	for image in images:
		file_path = image.get('file_url')
		ext = check_extension(file_path)
		if ext != "jrxml":
			#delete_jrxml_child_file(dt, jasper_all_sites)
			delete_jrxml_child_file(file_path.split("/files")[-1][1:], jasper_all_sites)

def write_file_jrxml(fname, content, dn=None, content_type=None, parent=None):
	dt = frappe.form_dict.doctype
	if dt == "Jasper Reports":
		wobj = WriteFileJrxml(dt, fname, content, parent)
		f = wobj.process(dn=dn)

		return f


def get_file_path(doc_file_path):
	return "".join(doc_file_path.split("/files")[-1][1:])

"""
def get_number_weekday_in_month(year, month, weekday, local=None):
	import calendar
	import locale


	if local:
		default_local = locale.getlocale(locale.LC_ALL)
		locale.setlocale(locale.LC_ALL, local)

	if isinstance(month, basestring):
		month = list(calendar.month_name).index(month.capitalize())

	first_weekday = calendar.firstweekday()
	calendar.setfirstweekday(calendar.MONDAY)
	weekday_number = getattr(calendar, weekday.upper())

	number = len([1 for i in calendar.monthcalendar(year, month) if i[weekday_number] != 0])

	if local:
		locale.setlocale(locale.LC_ALL, default_local[0])

	calendar.setfirstweekday(first_weekday)

	return number

"""
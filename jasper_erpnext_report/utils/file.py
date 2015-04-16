from __future__ import unicode_literals
__author__ = 'luissaguas'
import os, logging
import frappe
import frappe.model
import frappe.model.naming
from frappe import _
from jasper_erpnext_report.jasper_reports.compile_reports import jasper_compile
from frappe.utils import get_site_path
from frappe.utils.file_manager import save_file_on_filesystem, delete_file_from_filesystem, get_content_hash
from lxml import etree
import jasper_erpnext_report, json
from io import BytesIO

from jasper_erpnext_report.utils.jrxml import *

import mimetypes, re

jasper_ext_supported = ["jrxml", "jpg", "gif", "png", "bmp", "properties"]
_logger = logging.getLogger(frappe.__name__)

dataSourceExpressionRegExp = re.compile( r"""\$P\{(\w+)\}""" )

def get_image_name(iname):
	if not iname:
		return
	names = iname.split(os.sep)
	c = len(names)

	name = names[c-1]

	if '"' in name:
		c = len(name)
		name = name[1:c-1]
	return name


def get_compiled_path(dir_path, dn):
	jrxml_path = get_jrxml_path(dir_path, dn)
	compiled_path = frappe.utils.get_path("compiled", base=jrxml_path)
	frappe.create_folder(compiled_path)
	return compiled_path

def get_images_path(compiled_path):
	images_path = frappe.utils.get_path("images", base=compiled_path)
	frappe.create_folder(images_path)
	return images_path

def get_jrxml_path(dir_path, dn):
	jrxml_path = frappe.utils.get_path(dn, base=dir_path)
	return jrxml_path

def get_jasper_path(for_all_sites = False):
	if not for_all_sites:
		return 	get_site_path("jasper")

	module_path = os.path.normpath(os.path.join(os.path.dirname(jasper_erpnext_report.__file__), "jasper"))
	return module_path


def jasper_compile_jrxml(fname, file_path, compiled_path):
	c = len(fname) - 6
	jasper_compile(file_path, os.path.join(compiled_path, fname[:c] + ".jasper"))

def write_StringIO_to_file(file_path, output):
	write_file(output.getvalue(), file_path, modes="wb")

def write_file(content, file_path, modes="w+"):
	with open(file_path, modes) as f:
		f.write(content)
	return file_path

def check_extension(fname):
	ext = get_extension(fname)
	if ext and ext.lower() not in jasper_ext_supported:
		frappe.msgprint(_("Please select a file with extension jrxml."),
			raise_exception=True)
	return ext.lower()

def get_extension(fname):

	ext = fname.rsplit(".",1)

	if len(ext) > 1:
		return ext[1].lower()

	return ext[0]

def write_file_jrxml(fname, content, content_type=None, parent=None):
	path_join = os.path.join
	file_path = None
	dt = frappe.form_dict.doctype
	if dt == "Jasper Reports":
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
					if (ext!="properties"):
						image_path = xmldoc.get_image_path_from_jrxml(fname)
						file_path= path_join(compiled_path, os.path.normpath(image_path))
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
			if rname or check_root_exists(dt,dn,parent):
				frappe.msgprint(_("Remove first the file (%s) associated with this document or (%s) is a wrong parent." % (rname, rname)),
					raise_exception=True)
			jrxml_path = get_jrxml_path(jasper_path, dn)
			file_path = path_join(jrxml_path, fname)

			#check if the parent as this jrxml child
			docs = frappe.get_all("File Data", fields=["file_name", "file_url"], filters={"attached_to_name": dn, "attached_to_doctype": dt, "name": parent})
			if docs:
				xmldoc = JasperXmlReport(path_join(jrxml_path, docs[0].file_name))
				for sub in xmldoc.subreports:
					s = sub.rsplit("/",1)
					if len(s) > 1:
						if not (s[1][:-7] == fname[:-6]):
							frappe.msgprint(_("The report %s is not a subreport of %s."  % (fname[:-6], s[1][:-7])),raise_exception=True)
					elif not (sub[:-7] == fname[:-6]):
						frappe.msgprint(_("The report %s is not a subreport of %s."  % (fname[:-6], sub[:-7])),raise_exception=True)

			xmldoc = JasperXmlReport(BytesIO(content))
			xmldoc.change_subreport_expression_path()
			scriptlet = xmldoc.get_attrib("scriptletClass")
			if not scriptlet:
				pass

			xmldoc.change_path_images()
			xmldoc.setProperty("parent", parent)
			autofilename = frappe.model.naming.make_autoname("File.#####", doctype='')
			xmldoc.setProperty("jasperId", autofilename)

			content = xmldoc.toString()
		fpath = write_file(content, file_path)
		path =  os.path.relpath(fpath, jasper_path)
		if ext == "jrxml":
			jasper_compile_jrxml(fname, file_path, compiled_path)

		return {
			'name': autofilename or None,
			'file_name': os.path.basename(path),
			'file_url': os.sep + path.replace('\\','/'),
			"content": content
		}
	else:
		return save_file_on_filesystem(fname, content, content_type)

def check_root_exists(dt, dn, parent="root"):
	if not (parent == "root"):
		return False
	docs = frappe.get_all("File Data", fields=["file_name"], filters={"attached_to_name": dn, "attached_to_doctype": dt, "attached_to_report_name": "root"})
	return len(docs) > 0

def get_jrxml_root(dt,dn):
	docs = frappe.get_all("File Data", fields=["file_name", "file_url"], filters={"attached_to_name": dn, "attached_to_doctype": dt, "attached_to_report_name": "root"})
	return docs[0].file_name, docs[0].file_url

def check_if_jrxml_exists_db(dt, dn, fname, parent=None):

	docs = frappe.get_all("File Data", fields=["file_name"], filters={"attached_to_name": dn, "attached_to_doctype": dt, "name": parent})
	for doc in docs:
		jrxml_ext = get_extension(doc.file_name)
		if not (jrxml_ext == "jrxml"):
			return doc.file_name
		return doc.file_name if fname == doc.file_name else None
	return None


def delete_file_jrxml(doc):
	dt = doc.attached_to_doctype

	if dt == "Jasper Reports":
		dn = doc.attached_to_name
		ext = get_extension(doc.file_name)
		jasper_all_sites_report = frappe.db.get_value(dt, dn, 'jasper_all_sites_report')
		file_path = os.path.join(get_jasper_path(jasper_all_sites_report), doc.file_url[1:])
		path = os.path.normpath(os.path.join(file_path,".."))
		if ext == "jrxml":
			remove_directory(path)
			frappe.db.sql("""delete from `tab%s` where %s=%s """ % ("Jasper Parameter", "parent", '%s'),(dn), auto_commit=1)
			frappe.db.set_value(dt, dn, 'query', "")
		else:
			delete_jrxml_child_file(doc.file_url, jasper_all_sites_report)
	else:
		delete_file_from_filesystem(doc)


def delete_file_jrxml_old(doc):
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
	else:
		delete_file_from_filesystem(doc)

def delete_jrxml_child_file(path, jasper_all_sites):
	file_path = os.path.join(get_jasper_path(jasper_all_sites),path[1:])
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

def remove_from_doc(dt, dn, field, where_field = "name"):
	frappe.db.sql("""update `tab%s` set %s=NULL where %s=%s""" % (dt, field, where_field, '%s'),(dn))


def delete_from_doc(dt, dn, field, value, where_field):
	frappe.db.sql("""delete from `tab%s` where %s=%s and %s=%s""" % (dt, field, '%s',  where_field,'%s'),(value, dn), auto_commit=1)

def delete_from_FileData(dt, dn, file_url):
	frappe.db.sql("""delete from `tabFile Data` where attached_to_doctype=%s and attached_to_name=%s and file_url=%s""",(dt, dn, file_url), auto_commit=1)

def remove_directory(path, ignore_errors=True):
	import shutil
	shutil.rmtree(path, ignore_errors)

def remove_compiled_report(root_path):
	ncount = 0
	for root, dirs, files in os.walk(root_path, topdown=True):
		if root.endswith("compiled"):
			for name in dirs:
				remove_directory(os.path.join(root, name))
				ncount = ncount + 1
	return ncount

def get_file(path, modes="r", raise_not_found=False):
	content = None
	if modes != "r":
		content = read_file(path, modes=modes, raise_not_found=raise_not_found)
	else:
		content = frappe.read_file(path, raise_not_found=raise_not_found)

	return content

def read_file(path, modes="r", raise_not_found=False):
	content = None
	if os.path.exists(path):
		with open(path, modes) as f:
			content = f.read()
	elif raise_not_found:
		raise IOError("{} Not Found".format(path))
	return content

def get_html_reports_path(report_name, where="reports", hash=None, localsite=None):
	site = localsite or frappe.local.site
	path_jasper_module = os.path.dirname(jasper_erpnext_report.__file__)
	path = os.path.join(path_jasper_module, "public", where, site, report_name, hash)
	frappe.create_folder(path)
	return path

def get_html_reports_images_path(report_path, where="images"):
	path = os.path.join(report_path, where)
	frappe.create_folder(path)
	return path



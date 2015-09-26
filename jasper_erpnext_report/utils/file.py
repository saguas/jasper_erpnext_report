from __future__ import unicode_literals
__author__ = 'luissaguas'
import os, re
import frappe
from frappe import _
from frappe.utils import get_site_path
from frappe.utils.file_manager import get_content_hash
import jasper_erpnext_report

from jasper_erpnext_report.utils.jrxml import *


jasper_ext_supported = ["jrxml", "jpg", "gif", "png", "bmp", "properties", "xml"]

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


def get_images_path(compiled_path):
	images_path = frappe.utils.get_path("images", base=compiled_path)
	frappe.create_folder(images_path)
	return images_path

def get_jasper_path(for_all_sites = False):
	if not for_all_sites:
		return 	get_site_path("jasper")

	module_path = os.path.normpath(os.path.join(os.path.dirname(jasper_erpnext_report.__file__), "jasper"))
	return module_path


def write_StringIO_to_file(file_path, output):
	write_file(output.getvalue(), file_path, modes="wb")

def write_file(content, file_path, modes="w+"):
	with open(file_path, modes) as f:
		f.write(content)
	return file_path

def check_extension(fname):
	ext = get_extension(fname)
	if ext and ext.lower() not in jasper_ext_supported:
		frappe.msgprint(_("Please select a file with a supported extension."),
			raise_exception=True)
	return ext.lower()

def get_extension(fname):

	ext = fname.rsplit(".",1)

	if len(ext) > 1:
		return ext[1].lower()

	return ext[0]


def remove_from_doc(dt, dn, field, where_field = "name"):
	frappe.db.sql("""update `tab%s` set %s=NULL where %s=%s""" % (dt, field, where_field, '%s'),(dn))


def delete_from_doc(dt, dn, field, value, where_field):
	frappe.db.sql("""delete from `tab%s` where %s=%s and %s=%s""" % (dt, field, '%s',  where_field,'%s'),(value, dn), auto_commit=1)

def delete_from_FileData(dt, dn, file_url):
	frappe.db.sql("""delete from `tabFile` where attached_to_doctype=%s and attached_to_name=%s and file_url=%s""",(dt, dn, file_url), auto_commit=1)

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



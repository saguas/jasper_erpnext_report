__author__ = 'luissaguas'
import os, logging
import frappe
from frappe import _
from jasper_erpnext_report.jasper_reports.compile_reports import jasper_compile
#from utils import update_doctype_doc
from frappe.utils import get_site_path, get_site_base_path
from frappe.utils.file_manager import save_file_on_filesystem, delete_file_from_filesystem
#from jasperserver.report import Report
from xml.etree import ElementTree as ET
from lxml import etree
import jasper_erpnext_report
from jasper_erpnext_report.utils.utils import set_jasper_parameters
from frappe.modules.import_file import import_doc


jasper_ext_supported = ["jrxml", "jpg", "gif", "png", "bmp"]
_logger = logging.getLogger(frappe.__name__)


def get_image_name(iname):
	#if "/" in iname:
	#	names = iname.split("/")
	#else:
	#	names = iname.split("\\")
	names = iname.split(os.sep)
	c = len(names)

	name = names[c-1]

	if '"' in name:
		c = len(name)
		name = name[1:c-1]
	return name


def get_xml_elem(xmlfile, elem_name):
	tree = etree.parse(xmlfile) #.replace('\\', '/'))
	root = tree.getroot()
	print "root: {}".format(root.tag)
	nameSpace = root.tag.split('jasperReport')[0]
	if nameSpace:
		c = len(nameSpace) - 1
		elems = root.findall(".//j:" + elem_name, namespaces={'j':nameSpace[1:c]})
	else:
		elems = root.findall(".//" + elem_name)

	return elems

"""def get_xml_elem2(xmlfile, elem_name):
	parser = etree.XMLParser(ns_clean=True)
	tree = etree.parse(xmlfile, parser)
	root = tree.getroot()
	print "root: {}".format(root.tag)
	#nameSpace = root.tag.split('jasperReport')[0]
	#if nameSpace:
	#	c = len(nameSpace) - 1
	#	elems = root.findall(".//j:" + elem_name, namespaces={'j':nameSpace[1:c]})
	#else:
	#	elems = root.findall(".//" + elem_name)
	elems = root.findall(".//" + elem_name)

	return elems"""

def get_params(xmlfile):

	params = get_xml_elem(xmlfile, "parameter")

	return params

def get_query(xmlfile):

	query = get_xml_elem(xmlfile, "queryString")

	return query

def get_images(xmlfile):

	images = get_xml_elem(xmlfile, "imageExpression")

	return images

def _insert_params(pname, c_idx, parent, param_type):
	mydict = {"updateDate":frappe.utils.now()}
	doc = set_jasper_parameters(pname, parent, c_idx, mydict, param_type)
	print "Doc param {}".format(doc)
	import_doc(doc)

def insert_params(xmlfile, dn):
	params = get_params(xmlfile)
	c_idx = 0
	for param in params:
		pname = param.xpath('./@name')
		pclass = param.xpath('./@class')
		#if nameSpace:
		#	desc = param.xpath('.//j:parameterDescription', namespaces={'j':nameSpace[1:c]})
		#else:
		#	desc = param.xpath('.//parameterDescription')
		c_idx = c_idx + 1
		print "params: {}".format(dn)
		ptype = pclass[0].split(".")
		c = len(ptype) - 1
		_insert_params(pname[0], c_idx, dn, ptype[c].lower())

	return params

def lxml_parser_images(image_name, xmlfile):
	image_path = None
	images = get_xml_elem(xmlfile, "imageExpression")
	for image in images:
		fimage = get_image_name(image.text)
		if fimage == image_name:
			image_path = fimage
		break

	return image_path

def get_image_path_from_jrxml(image_name, jrxml_path):

	image_path = lxml_parser_images(image_name, jrxml_path)

	if not image_path:
		frappe.msgprint(_("This image (%s) don't exist in this report" % image_name),
			raise_exception=True)

	return image_path

def get_compiled_path(dir_path, dn):
	path_join = os.path.join
	jrxml_path = path_join(dir_path, dn)
	compiled_path = path_join(jrxml_path, "compiled")
	frappe.create_folder(compiled_path)
	return compiled_path

def get_images_path(compiled_path):
	path_join = os.path.join
	images_path = path_join(compiled_path, "images")
	frappe.create_folder(images_path)
	return images_path

def get_jrxml_path(dir_path, dn):
	path_join = os.path.join
	jrxml_path = path_join(dir_path, dn)
	return jrxml_path

def get_jasper_path(for_all_sites = False):
	jasper_path = None
	if not for_all_sites:
		return 	get_site_path("jasper")
	#print "os.path.dirname(__file__) {}".format(os.path.dirname(jasper_erpnext_report.__file__))
	#this module path
	module_path = os.path.dirname(jasper_erpnext_report.__file__)
	#root_sites_path = os.path.normpath(os.path.join(get_site_base_path(), ".."))
	#root_sites_path = os.path.normpath(os.path.join(module_path, ".."))
	#return os.path.join(root_sites_path, "jasper")
	return os.path.join(module_path, "jasper")


def jasper_compile_jrxml(fname, dt, dn, file_path, compiled_path):
	c = len(fname) - 6
	jasper_compile(file_path, os.path.join(compiled_path, fname[:c] + ".jasper"))
	#update_doctype_doc(dt, dn, file_path)

def write_StringIO_to_file(file_path, output):
	write_file(output.getvalue(), file_path, modes="wb")

def write_file(content, file_path, modes="w+"):
	# write the file
	with open(file_path, modes) as f:
		f.write(content)
	return file_path

def check_extension(fname):
	ext = get_extension(fname)
	if ext and ext.lower() not in jasper_ext_supported:
		frappe.msgprint(_("Please select a file with extension jrxml"),
			raise_exception=True)
	return ext.lower()

def get_extension(fname):
	ext = fname.split(".")
	if len(ext) > 1:
		return ext[1]
	return None

def write_file_jrxml(fname, content, content_type):
	path_join = os.path.join
	dt = frappe.form_dict.doctype
	if dt == "Jasper Reports":
		ext = check_extension(fname)
		dn = frappe.form_dict.docname
		jasper_all_sites_report = frappe.db.get_value(dt, dn, 'jasper_all_sites_report')
		jasper_path = get_jasper_path(jasper_all_sites_report)
		compiled_path = get_compiled_path(jasper_path, dn)
		if ext != "jrxml":
			#image_path= get_images_path(compiled_path)
			docs = frappe.get_all("File Data", fields=["file_name", "file_url"], filters={"attached_to_name": dn, "attached_to_doctype": dt})
			if not docs:
				frappe.msgprint(_("Add a report file for this report first"),
			raise_exception=True)
			for doc in docs:
				jrxml_ext = get_extension(doc.file_name)
				if jrxml_ext == "jrxml":
					jrxml_os_path = path_join(jasper_path, doc.file_url[1:])
					image_path = get_image_path_from_jrxml(fname, jrxml_os_path)
					file_path= path_join(compiled_path, os.path.normpath(image_path))
					print "image_path {0}".format(file_path)
					break
			#file_path = path_join(image_path, fname)
		else:
			rname = check_if_jrxml_exists_db(dt, dn)
			if rname:
				frappe.msgprint(_("Remove first the report file (%s) associated with this doc!" % (rname)),
					raise_exception=True)
			jrxml_path = get_jrxml_path(jasper_path, dn)
			file_path = path_join(jrxml_path, fname)
		#print "content report file {}".format(content)
		fpath = write_file(content, file_path)
		#file_path, compiled_path = get_files_path(fname, dn, jasper_path, ext)
		path =  os.path.relpath(fpath, jasper_path)
		if ext == "jrxml":
			jasper_compile_jrxml(fname, dt, dn, file_path, compiled_path)
			#update_doc(dt, dn, "jasper_upload_jrxml", path)
			#insert_params(file_path, dn)

		#else:
			#pass
			#update_doc("Jasper Report Image", dn, 'jasper_report_image', path, "parent")
		#	insert_doc(dt, dn, fname, 'jasper_report_image', '/' + path, 'jasper_report_images', "Jasper Report Image")

		return {
			'file_name': os.path.basename(path),
			'file_url': os.sep + path.replace('\\','/')
		}
	else:
		return save_file_on_filesystem(fname, content, content_type)


def check_if_jrxml_exists_db(dt, dn):
	fname = None
	docs = frappe.get_all("File Data", fields=["file_name"], filters={"attached_to_name": dn, "attached_to_doctype": dt})
	for doc in docs:
		jrxml_ext = get_extension(doc.file_name)
		if jrxml_ext == "jrxml":
			fname = doc.file_name
			break
	return fname

def delete_file_jrxml(doc):
	print "deleteing jrxml"
	dt = doc.attached_to_doctype
	if dt == "Jasper Reports":
		dn = doc.attached_to_name
		ext = get_extension(doc.file_name)
		jasper_all_sites_report = frappe.db.get_value(dt, dn, 'jasper_all_sites_report')
		file_path = os.path.join(get_jasper_path(jasper_all_sites_report), doc.file_url[1:])
		if os.path.exists(file_path) and ext == "jrxml":
			os.remove(file_path)
			_remove_compiled(doc.file_name, dn, jasper_all_sites_report)
			delete_jrxml_images(dt, dn, jasper_all_sites_report)
			frappe.db.sql("""delete from `tab%s` where %s=%s """ % ("Jasper Parameter", "parent", '%s'),(dn), auto_commit=1)
			frappe.db.set_value(dt, dn, 'query', "")
		else:
			delete_jrxml_image(dt, dn, doc.file_url, jasper_all_sites_report)
	else:
		delete_file_from_filesystem(doc)

def _remove_compiled(file_name, dn, jasper_all_sites = False):
	jasper_path = get_jasper_path(jasper_all_sites)
	compiled_path = get_compiled_path(jasper_path, dn)
	if os.path.exists(compiled_path):
		c = len(file_name) - 6
		file_to_remove = os.path.join(compiled_path, file_name[:c] + ".jasper")
		if os.path.exists(file_to_remove):
			os.remove(file_to_remove)
			remove_from_doc("Jasper Reports", dn, 'jasper_upload_jrxml')

def delete_jrxml_image(dt, dn, path, jasper_all_sites):
	_logger.info("jasperserver delete_jrxml_images images {}".format(path))
	file_path = os.path.join(get_jasper_path(jasper_all_sites),path[1:])
	if os.path.exists(file_path):
		print "a apagar {0} dt {1}".format(file_path, dt)
		os.remove(file_path)
		#remove_from_doc("Jasper Report Image", dn, 'jasper_report_image', 'parent')
		delete_from_doc("Jasper Report Image", dn, 'jasper_report_image', path, 'parent')
		delete_from_FileData(dt, dn, path)
		#frappe.db.sql("""update `tabJasper Reports` set jasper_report_images=NULL where name=%s""",
		#	(dn))

#delete all images associated to jrxml file
def delete_jrxml_images(dt, dn, jasper_all_sites = False):
	images = frappe.get_all("File Data", fields=["file_url"], filters={"attached_to_name": dn, "attached_to_doctype": dt})
	for image in images:
		file_path = image.get('file_url')
		ext = check_extension(file_path)
		if ext != "jrxml":
			delete_jrxml_image(dt, dn, file_path, jasper_all_sites)

def remove_from_doc(dt, dn, field, where_field = "name"):
	frappe.db.sql("""update `tab%s` set %s=NULL where %s=%s""" % (dt, field, where_field, '%s'),(dn))

# def update_doc(dt, dn, field, value, where_field = "name"):
# 	frappe.db.sql("""update `tab%s` set %s=%s where %s=%s""" % (dt, field,'%s', where_field, '%s'),
# 						(value, dn))

def delete_from_doc(dt, dn, field, value, where_field):
	#print """delete from `tab%s` where %s=%s and %s=%s""" % (dt, field, value,  where_field,dn)
	frappe.db.sql("""delete from `tab%s` where %s=%s and %s=%s""" % (dt, field, '%s',  where_field,'%s'),(value, dn), auto_commit=1)

def delete_from_FileData(dt, dn, file_url):
	#print """delete from `tab%s` where %s=%s and %s=%s""" % (dt, field, value,  where_field,dn)
	frappe.db.sql("""delete from `tabFile Data` where attached_to_doctype=%s and attached_to_name=%s and file_url=%s""",(dt, dn, file_url), auto_commit=1)

def remove_directory(path):
	import shutil
	shutil.rmtree(path)

def remove_compiled_report(root_path):
	ncount = 0
	for root, dirs, files in os.walk(root_path, topdown=True):
		if root.endswith("compiled"):
			for name in dirs:
				remove_directory(os.path.join(root, name))
				print "directory a remover is {}".format(os.path.join(root, name))
				ncount = ncount + 1
	return ncount

def get_file(path, modes="r"):
	with open(path, modes) as f:
		content = f.read()
	return content

def get_html_reports_path(report_name, where="reports", hash=None, localsite=None):
	site = localsite or frappe.local.site
	path_jasper_module = os.path.dirname(jasper_erpnext_report.__file__)
	path = os.path.join(path_jasper_module, "public", where, site, report_name, hash)
	frappe.create_folder(path)
	return path

def get_html_reports_images_path(report_path, where="images"):
	#path = get_html_reports_path(fileName, where=where)
	path = os.path.join(report_path, where)
	frappe.create_folder(path)
	return path

# def insert_doc(dt, dn, fname, field, value, parentfield, doc_report):
# 	mydict = {"updateDate":frappe.utils.now()}
# 	doc = _doctype_from_jasper_doc(fname, doc_report, mydict)
# 	#print "mydict {}".format(frappe.db.sql("""select count(*) as total from `tabJasper Report Image` where parent=%s""", dn)[0][0])
# 	c_idx = frappe.db.sql("""select count(*) as total from `tab%s` where parent=%s""" % (doc_report, '%s'), dn)[0][0] + 1
# 	print "idx {}".format(c_idx)
# 	doc['idx'] = c_idx
# 	doc[field] = value
# 	doc["parent"] = dn
# 	doc["parentfield"] = parentfield
# 	doc["parenttype"] = dt
# 	import_doc(doc)

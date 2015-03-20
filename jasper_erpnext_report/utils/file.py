from __future__ import unicode_literals
__author__ = 'luissaguas'
import os, logging
import frappe
from frappe import _
from jasper_erpnext_report.jasper_reports.compile_reports import jasper_compile
from frappe.utils import get_site_path, cstr
from frappe.utils.file_manager import save_file_on_filesystem, delete_file_from_filesystem, get_uploaded_content, check_max_file_size, get_content_hash
from lxml import etree
import jasper_erpnext_report, json
from io import BytesIO
from jasper_erpnext_report.utils.utils import set_jasper_parameters
from frappe.modules.import_file import import_doc

import mimetypes, re

jasper_ext_supported = ["jrxml", "jpg", "gif", "png", "bmp", "properties"]
_logger = logging.getLogger(frappe.__name__)

dataSourceExpressionRegExp = re.compile( r"""\$P\{(\w+)\}""" )

def get_image_name(iname):
	#if "/" in iname:
	#	names = iname.split("/")
	#else:
	#	names = iname.split("\\")
	if not iname:
		return
	names = iname.split(os.sep)
	c = len(names)

	name = names[c-1]

	if '"' in name:
		c = len(name)
		name = name[1:c-1]
	return name


class JasperXmlReport():
	def __init__(self, xmlfile=''):
		self.xmldoc = etree.parse(xmlfile)
		self.ns = 'http://jasperreports.sourceforge.net/jasperreports'
		self.nss = {'jr': self.ns}
		self._language = 'xpath'
		self._querystring = ''
		self._relations = []
		self._fields = {}
		self._fieldNames = []
		self._subreports = []
		self._datasets = []
		self._jasper_prefix = "compiled/"
		self._name = self.get_attrib("name")
		self.get_query_from_xml()
		self.get_xml_subreports()
		self.get_xml_subdataset_query()


	@property
	def name(self):
		return self._name

	@property
	def language(self):
		return self._language

	@property
	def queryString(self):
		return self._querystring

	@property
	def fields(self):
		return self._fields

	@property
	def fieldNames(self):
		return self._fieldNames

	@property
	def subreports(self):
		return self._subreports

	@property
	def datasets(self):
		return self._datasets

	def subreportDirectory(self):
		pass

	def standardDirectory(self):
		pass

	def set_attrib(self, attr, value, elem=None):
		#root = self.xmldoc.getroot()
		if elem == "root" or elem == "/" or elem is None:
			elem = "jasperReport"
		root = self.xmldoc.xpath( '//jr:' + elem, namespaces=self.nss)
		root[0].set(attr,value) if root else None

	def setProperty(self, name, value):
		root = self.xmldoc.getroot()
		root.insert(0, etree.Element("property", name=name, value=value))
		#element = etree.SubElement(self.xmldoc.getroot(),"property", name=name, value=value)
		#element.set(name, value)
		return

	def getProperty(self, name, elem=None):
		if elem == "root" or elem == "/" or elem is None:
			elem = "jasperReport"
		value = None
		prop = self.xmldoc.xpath( '//jr:'+ elem + '/jr:property[@name="'+ name +'"]', namespaces=self.nss)
		#print "jasperreports xml getProperty 5 {} name {}".format(prop and 'value' in prop[0].keys(), self.name)
		if prop and 'value' in prop[0].keys():
			value = prop[0].get('value')
		return value

	def get_attrib(self, attr, elem=None):
		if elem == "root" or elem == "/" or elem is None:
			elem = "jasperReport"
		root = self.xmldoc.xpath( '//jr:' + elem, namespaces=self.nss)
		return root and root[0].get(attr)

	def toString(self):
		self.get_xml_subdataset_query()
		return etree.tostring(self.xmldoc.getroot())

	def get_xml_elem(self, elem_name):
		#elemTags = self.xmldoc.xpath( '/jr:jasperReport/jr:' + elem_name, namespaces=self.nss)
		root = self.xmldoc.xpath( '//jr:' + elem_name, namespaces=self.nss)
		return root

	def get_xml_subreports(self):
		subreports = self.xmldoc.xpath( '//jr:subreport', namespaces=self.nss)
		for subreport in subreports:

			subreportExpression = subreport.find('{%s}subreportExpression' % self.ns, '')
			if subreportExpression is None:
				continue
			try:
				#subtext = json.loads(subreportExpression.text.strip())
				subtext = json.loads(frappe.utils.strip(subreportExpression.text))
			except:
				#subtext = subreportExpression.text.strip()
				subtext = frappe.utils.strip(subreportExpression.text)

			print "subreports xml 9 {} {} {}".format(subreportExpression, subreportExpression.text, subtext)
			self._subreports.append(subtext)

	def change_subreport_expression_path(self):
		del self._subreports[:]
		subreports = self.xmldoc.xpath( '//jr:subreport', namespaces=self.nss)
		for subreport in subreports:

			subreportExpression = subreport.find('{%s}subreportExpression' % self.ns, '')
			if subreportExpression is None:
				continue
			try:
				#subtext = json.loads(subreportExpression.text.strip())
				subtext = json.loads(frappe.utils.strip(subreportExpression.text))
			except:
				#subtext = subreportExpression.text.strip()
				subtext = frappe.utils.strip(subreportExpression.text)

			print "subreports xml 9 {} {} {}".format(subreportExpression, subreportExpression.text, subtext)

			if subtext.endswith('.jrxml'):
				s = subtext.rsplit("/", 1)
				if len(s) > 1:
					rname = s[1][:-5] + "jasper"
				else:
					rname = subtext[:-5] + "jasper"
			elif subtext.endswith('.jasper'):
				s = subtext.rsplit("/", 1)
				if len(s) > 1:
					rname = s[1]
				else:
					rname = subtext
			else:
				continue
			new_path = self._jasper_prefix + rname
			subreportExpression.text = json.dumps(frappe.utils.escape_html(new_path))
			self._subreports.append(new_path)

	def get_xml_subdataset_query(self):
		subdatasets = self.xmldoc.xpath( '//jr:subDataset', namespaces=self.nss)
		for subdataset in subdatasets:
			name = subdataset.attrib["name"]
			print "name attrib {}".format(name)
			queryString = subdataset.find('{%s}queryString' % self.ns, '')
			if queryString is None:
				continue
			try:
				#subquery = json.loads(queryString.text.strip())
				subquery = json.loads(frappe.utils.strip(queryString.text))
			except:
				#subquery = queryString.text.strip()
				subquery = frappe.utils.strip(queryString.text)

			self._datasets.append({"name": name, "query": subquery})

	"""
	def get_xml_dataset(self):
		datasetTags = self.xmldoc.xpath( '//jr:datasetRun', namespaces=self.nss)
		for tag in datasetTags:
			dataSourceExpression = tag.findtext('{%s}dataSourceExpression' % self.ns, '')
			if not dataSourceExpression:
				continue
			dataSourceExpression = dataSourceExpression.strip()
			m = dataSourceExpressionRegExp.match( dataSourceExpression )
			if not m:
				continue
			dataSourceExpression = m.group(1)
			if dataSourceExpression == 'REPORT_DATA_SOURCE':
				continue
			subDatasetName = tag.get('subDataset')
			if not subDatasetName:
				continue
			dataset = JasperXmlReport()
			self._subreports.append({
				'parameter': dataSourceExpression,
				'report': dataset,
				'filename': 'DATASET',
			})

	def safe_eval(self):
		pass
	"""

	"""
	def get_xml_elem2(xmlfile, elem_name):
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
	"""

	def get_params(self):

		params = self.get_xml_elem("parameter")

		return params

	def get_query(self):

		query =self.get_xml_elem("queryString")
		if query and query[0].text:
			self._querystring = query[0].text

		if query and query[0].get('language'):
			self._language = query[0].get('language').lower()

		return query

	def change_path_images(self):
		images = self.xmldoc.xpath( '//jr:imageExpression', namespaces=self.nss)
		for image in images:
			try:
				#txt = json.loads(image.text.strip())
				txt = json.loads(frappe.utils.strip(image.text))
			except:
				#txt = image.text.strip()
				txt = frappe.utils.strip(image.text)
			if txt.startswith("/"):
				image.text = json.dumps(txt[1:])
				#image.text = txt[1:]
		return images

	def get_images(self):
		self._images = self.xmldoc.xpath( '//jr:imageExpression', namespaces=self.nss)
		return self._images

	def lxml_parser_images(self, image_name):
		image_path = None
		#images = self.get_xml_elem("imageExpression")
		images = self.get_images()
		for image in images:
			#fimage = get_image_name(image.text)
			try:
				fimage = json.loads(image.text)
			except:
				fimage = image.text
				
			s = fimage.rsplit("/",1)
			if len (s) > 1:
				if s[1] == image_name:
					image_path = fimage
			else:
				if fimage == image_name:
					image_path = fimage
			break

		return image_path

	def get_image_path_from_jrxml(self, image_name):

		image_path = self.lxml_parser_images(image_name)

		if not image_path:
			frappe.msgprint(_("This image (%s) don't exist in this report" % image_name),
				raise_exception=True)

		return image_path

	def get_params_from_xml(self):
		return self.get_params()

	def get_query_from_xml(self):
		return self.get_query()

	def get_images_from_xml(self):
		return self.get_images()

"""
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
"""

def get_compiled_path(dir_path, dn):
	#path_join = os.path.join
	#jrxml_path = path_join(dir_path, dn)
	jrxml_path = get_jrxml_path(dir_path, dn)
	#compiled_path = path_join(jrxml_path, "compiled")
	compiled_path = frappe.utils.get_path("compiled", base=jrxml_path)
	frappe.create_folder(compiled_path)
	return compiled_path

def get_images_path(compiled_path):
	#path_join = os.path.join
	#images_path = path_join(compiled_path, "images")
	images_path = frappe.utils.get_path("images", base=compiled_path)
	frappe.create_folder(images_path)
	return images_path

def get_jrxml_path(dir_path, dn):
	#path_join = os.path.join
	#jrxml_path = path_join(dir_path, dn)
	jrxml_path = frappe.utils.get_path(dn, base=dir_path)
	return jrxml_path

def get_jasper_path(for_all_sites = False):
	if not for_all_sites:
		return 	get_site_path("jasper")
	#module_path = os.path.dirname(jasper_erpnext_report.__file__)
	module_path = frappe.get_module_path("jasper_erpnext_report", "..", "jasper")
	print "jasper_erpnext_report module path 2 {}".format(module_path)
	#return os.path.join(module_path, "jasper")
	return module_path


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
	ext = fname.rsplit(".",1)
	if len(ext) > 1:
		return ext[1].lower()
	return None

def write_file_jrxml(fname, content, content_type=None, parent=None):
	path_join = os.path.join
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
				frappe.msgprint(_("Add a report file first"), raise_exception=True)
			for doc in docs:
				jrxml_ext = get_extension(doc.file_name)
				if jrxml_ext == "jrxml":
					jrxml_os_path = path_join(jasper_path, doc.file_url[1:])
					xmldoc = JasperXmlReport(jrxml_os_path)
					if (ext!="properties"):
						image_path = xmldoc.get_image_path_from_jrxml(fname)
					#falta criar as pastas das imagens, para isso tenho de extranir o nome do path
						file_path= path_join(compiled_path, os.path.normpath(image_path))
					else:
						value = xmldoc.get_attrib("resourceBundle")
						if not value or value not in fname:
							frappe.msgprint(_("This report does't have %s as properties" % (fname,)),raise_exception=True)
						file_path= path_join(compiled_path, os.path.normpath(fname))
					print "image_path {0}".format(file_path)
					break
				else:
					frappe.msgprint(_("Add a report file for this report first"),raise_exception=True)
			#file_path = path_join(image_path, fname)
		else:
			#rname = check_if_jrxml_exists_db(dt, dn, fname, parent)
			#if rname and False:
			rname = check_if_jrxml_exists_db(dt, dn, fname, parent)
			if rname or check_root_exists(dt,dn,parent):
				frappe.msgprint(_("Remove first the report file (%s) associated with this doc or (%s) is a wrong parent !" % (rname, rname)),
					raise_exception=True)
			jrxml_path = get_jrxml_path(jasper_path, dn)
			file_path = path_join(jrxml_path, fname)

			#check if the parent as this jrxml child
			docs = frappe.get_all("File Data", fields=["file_name", "file_url"], filters={"attached_to_name": dn, "attached_to_doctype": dt, "name": parent})
			if docs:
				#parent_content = get_file(path_join(jrxml_path, docs[0].file_name))
				#xmldoc = JasperXmlReport(BytesIO(parent_content))
				xmldoc = JasperXmlReport(path_join(jrxml_path, docs[0].file_name))
				for sub in xmldoc.subreports:
					s = sub.rsplit("/",1)
					if len(s) > 1:
						if not (s[1][:-7] == fname[:-6]):
							frappe.msgprint(_("The report %s is not a sub report of %s"  % (fname[:-6], s[1][:-7])),raise_exception=True)
					elif not (sub[:-7] == fname[:-6]):
						frappe.msgprint(_("The report %s is not a sub report of %s"  % (fname[:-6], sub[:-7])),raise_exception=True)

			xmldoc = JasperXmlReport(BytesIO(content))
			xmldoc.change_subreport_expression_path()
			scriptlet = xmldoc.get_attrib("scriptletClass")
			if not scriptlet:
				pass
				#xmldoc.set_attrib("scriptletClass", frappe.conf.scriptlet or jasper_erpnext_report.scriptlet)
			#mydoc = frappe.get_doc(dt,dn)
			#mydoc.query = "teste 1234"
			#mydoc.save()
			#print "subDataset name 2 {}".format(xmldoc.get_attrib("name", "/"))

			xmldoc.change_path_images()
			xmldoc.setProperty("parent", parent)
			autofilename = frappe.model.naming.make_autoname("File.#####", doctype='')
			xmldoc.setProperty("jasperId", autofilename)
			#xmldoc.setProperty("file_name", os.path.basename(path))

			content = xmldoc.toString()
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
		#parent must be jrxml
		if not (jrxml_ext == "jrxml"):
			return doc.file_name
		return doc.file_name if fname == doc.file_name else None
	return None


def delete_file_jrxml(doc):
	dt = doc.attached_to_doctype
	print "deleteing jrxml 2 dt {}".format(dt)

	if dt == "Jasper Reports":
		dn = doc.attached_to_name
		ext = get_extension(doc.file_name)
		jasper_all_sites_report = frappe.db.get_value(dt, dn, 'jasper_all_sites_report')
		file_path = os.path.join(get_jasper_path(jasper_all_sites_report), doc.file_url[1:])
		#path = file_path.rsplit("/",1)[0]
		path = os.path.normpath(os.path.join(file_path,".."))
		if ext == "jrxml":
			#print "jasper_path in delete_file jrxml 2 {} {}".format(path, file_path.rsplit("/",1)[0])
			remove_directory(path)
			#_remove_compiled(doc.file_name, dn, jasper_all_sites_report)
			#delete_jrxml_images(dt, dn, jasper_all_sites_report)
			frappe.db.sql("""delete from `tab%s` where %s=%s """ % ("Jasper Parameter", "parent", '%s'),(dn), auto_commit=1)
			frappe.db.set_value(dt, dn, 'query', "")
		else:
			delete_jrxml_child_file(doc.file_url, jasper_all_sites_report)
	else:
		delete_file_from_filesystem(doc)


def delete_file_jrxml_old(doc):
	print "deleteing jrxml"
	dt = doc.attached_to_doctype
	if dt == "Jasper Reports":
		dn = doc.attached_to_name
		ext = get_extension(doc.file_name)
		jasper_all_sites_report = frappe.db.get_value(dt, dn, 'jasper_all_sites_report')
		file_path = os.path.join(get_jasper_path(jasper_all_sites_report), doc.file_url[1:])
		if os.path.exists(file_path) and ext == "jrxml":
			os.remove(file_path)
			#_remove_compiled(doc.file_name, dn, jasper_all_sites_report)
			delete_jrxml_images(dt, dn, jasper_all_sites_report)
			frappe.db.sql("""delete from `tab%s` where %s=%s """ % ("Jasper Parameter", "parent", '%s'),(dn), auto_commit=1)
			frappe.db.set_value(dt, dn, 'query', "")
		else:
			delete_jrxml_child_file(dt, dn, doc.file_url, jasper_all_sites_report)
	else:
		delete_file_from_filesystem(doc)

"""
def _remove_compiled(file_name, dn, jasper_all_sites = False):
	jasper_path = get_jasper_path(jasper_all_sites)
	compiled_path = get_compiled_path(jasper_path, dn)
	if os.path.exists(compiled_path):
		c = len(file_name) - 6
		file_to_remove = os.path.join(compiled_path, file_name[:c] + ".jasper")
		if os.path.exists(file_to_remove):
			os.remove(file_to_remove)
			remove_from_doc("Jasper Reports", dn, 'jasper_upload_jrxml')
"""

def delete_jrxml_child_file(path, jasper_all_sites):
	file_path = os.path.join(get_jasper_path(jasper_all_sites),path[1:])
	if os.path.exists(file_path):
		os.remove(file_path)
		#delete_from_FileData(dt, dn, path)

#delete all images associated to jrxml file
def delete_jrxml_images(dt, dn, jasper_all_sites = False):
	images = frappe.get_all("File Data", fields=["file_url"], filters={"attached_to_name": dn, "attached_to_doctype": dt})
	for image in images:
		file_path = image.get('file_url')
		ext = check_extension(file_path)
		if ext != "jrxml":
			delete_jrxml_child_file(dt, dn, file_path, jasper_all_sites)

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

def remove_directory(path, ignore_errors=True):
	import shutil
	shutil.rmtree(path, ignore_errors)

def remove_compiled_report(root_path):
	ncount = 0
	for root, dirs, files in os.walk(root_path, topdown=True):
		if root.endswith("compiled"):
			for name in dirs:
				remove_directory(os.path.join(root, name))
				print "directory a remover is {}".format(os.path.join(root, name))
				ncount = ncount + 1
	return ncount

def get_file(path, modes="r", raise_not_found=False):
	content = None
	if modes != "r":
		if os.path.exists(path):
			with open(path, modes) as f:
				content = f.read()
		elif raise_not_found:
			raise IOError("{} Not Found".format(path))
	else:
		content = frappe.read_file(path, raise_not_found=raise_not_found)

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


def save_upload_file(fname, content, dt, dn, parent=None):

	#fname = get_file_name(fname)
	content_type = mimetypes.guess_type(fname)[0]
	file_size = check_max_file_size(content)
	file_data = write_file_jrxml(fname, content, content_type=content_type, parent=parent)
	content_hash = get_content_hash(file_data.pop("content"))

	#file_data.pop("content")

	file_data.update({
		"doctype": "File Data",
		"attached_to_report_name":parent,
		"attached_to_doctype": dt,
		"attached_to_name": dn,
		"file_size": file_size,
		"content_hash": content_hash,
	})

	f = frappe.get_doc(file_data)
	f.ignore_permissions = True
	#print "make_autoname(key, doctype='') {}".format(frappe.model.naming.make_autoname("File.#####", doctype=''))
	try:
		f.insert()
	except frappe.DuplicateEntryError:
		return frappe.get_doc("File Data", f.duplicate_entry)
	return f

def save_uploaded(dt, dn, parent):
	fname, content = get_uploaded_content()
	if content:
		return save_upload_file(fname, content, dt, dn, parent)
	else:
		raise Exception

"""
Function called to upload files from client
"""
def file_upload():
	#only administrator can upload reports!!
	print "called test upload 3 {}".format(frappe.form_dict)
	dt = frappe.form_dict.doctype
	dn = frappe.form_dict.docname
	parent = frappe.form_dict.parent_report
	filename = frappe.form_dict.filename

	if not filename:
		frappe.msgprint(_("Please select a file"),
			raise_exception=True)

	filedata = save_uploaded(dt, dn, parent)

	if dt and dn:
		comment = frappe.get_doc(dt, dn).add_comment("Attachment",
			_("Added {0}").format("<a href='{file_url}' target='_blank'>{file_name}</a>".format(**filedata.as_dict())))

	return {
		"name": filedata.name,
		"file_name": filedata.file_name,
		"file_url": filedata.file_url,
		"parent_report": parent,
		"comment": comment.as_dict()
	}


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

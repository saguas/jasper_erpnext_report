from __future__ import unicode_literals
__author__ = 'luissaguas'

import frappe
from frappe import _
from lxml import etree
import json

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
		if elem == "root" or elem == "/" or elem is None:
			elem = "jasperReport"
		root = self.xmldoc.xpath( '//jr:' + elem, namespaces=self.nss)
		root[0].set(attr,value) if root else None

	def setProperty(self, name, value):
		root = self.xmldoc.getroot()
		root.insert(0, etree.Element("property", name=name, value=value))
		return

	def getProperty(self, name, elem=None):
		if elem == "root" or elem == "/" or elem is None:
			elem = "jasperReport"
		value = None
		prop = self.xmldoc.xpath( '//jr:'+ elem + '/jr:property[@name="'+ name +'"]', namespaces=self.nss)
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
		root = self.xmldoc.xpath( '//jr:' + elem_name, namespaces=self.nss)
		return root

	def get_xml_subreports(self):
		subreports = self.xmldoc.xpath( '//jr:subreport', namespaces=self.nss)
		for subreport in subreports:

			subreportExpression = subreport.find('{%s}subreportExpression' % self.ns, '')
			if subreportExpression is None:
				continue
			try:
				subtext = json.loads(frappe.utils.strip(subreportExpression.text))
			except:
				subtext = frappe.utils.strip(subreportExpression.text)

			self._subreports.append(subtext)

	def change_subreport_expression_path(self):
		del self._subreports[:]
		subreports = self.xmldoc.xpath( '//jr:subreport', namespaces=self.nss)
		for subreport in subreports:

			subreportExpression = subreport.find('{%s}subreportExpression' % self.ns, '')
			if subreportExpression is None:
				continue
			try:
				subtext = json.loads(frappe.utils.strip(subreportExpression.text))
			except:
				subtext = frappe.utils.strip(subreportExpression.text)

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
			queryString = subdataset.find('{%s}queryString' % self.ns, '')
			if queryString is None:
				continue
			try:
				subquery = json.loads(frappe.utils.strip(queryString.text))
			except:
				subquery = frappe.utils.strip(queryString.text)

			self._datasets.append({"name": name, "query": subquery})

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
				txt = json.loads(frappe.utils.strip(image.text))
			except:
				txt = frappe.utils.strip(image.text)
			if txt.startswith("/"):
				image.text = json.dumps(txt[1:])
		return images

	def get_images(self):
		self._images = self.xmldoc.xpath( '//jr:imageExpression', namespaces=self.nss)
		return self._images

	def lxml_parser_images(self, image_name):
		image_path = None
		images = self.get_images()
		for image in images:
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
			frappe.msgprint(_("This image (%s) don't exist in this report." % image_name),
				raise_exception=True)

		return image_path

	def get_params_from_xml(self):
		return self.get_params()

	def get_query_from_xml(self):
		return self.get_query()

	def get_images_from_xml(self):
		return self.get_images()

__author__ = 'saguas'

import frappe
from jnius import PythonJavaClass, java_method


class JasperCustomDataSourceDefault(object):
	""" Get fields for each id """
	def __init__(self, ids):
		if isinstance(ids, basestring):
			ids = [ids]
		self.ids = ids
		self.currididx = -1
		self.totalrows = len(ids)
		self.count = 0

	def next(self):
		ret = True
		print "next 2 was called"
		self.currididx += 1
		if self.currididx >= self.totalrows:
			ret = False
		else:
			self.docname = self.ids[self.currididx]

		return ret

	def moveFirst(self):
		print "movefirst 2 was called"
		self.currididx = 0

	def getFieldValue(self, field, doctype=None):
		print "getFieldValue 2 was called {} doctype {}".format(field, doctype)

		na = field.split(":")
		l = len(na)
		if l > 2:
			doctype = na[0]
			self.docname = na[1]
			field = na[2]
		elif l > 1:
			self.docname = na[0]
			field = na[1]

		#doc = frappe.get_all(doctype, fields=[field], filters = {"name":docname})
		value = frappe.db.get_value(doctype, filters=self.docname, fieldname=field)

		return value


class _JasperCustomDataSource(PythonJavaClass):
	__javainterfaces__ = ['IFrappeDataSource']

	def __init__(self, jds, doctype=None):
		super(_JasperCustomDataSource, self).__init__()
		self.jds = jds
		self.doctype = doctype

	@java_method('()Z')
	def next(self):
		return self.jds.next()

	@java_method('()')
	def moveFirst(self):
		return self.jds.moveFirst()

	@java_method('(Ljava/lang/String;)Ljava/lang/String;')
	def getFieldValue(self, fname):
		return self.jds.getFieldValue(fname, doctype=self.doctype)



print "FrappeDataSource Initialized"
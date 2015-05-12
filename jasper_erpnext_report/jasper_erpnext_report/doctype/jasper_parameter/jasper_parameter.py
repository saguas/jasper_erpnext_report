# Copyright (c) 2013, Luis Fernandes and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class JasperParameter(Document):

	def autoname(self, method=None):
		#field:jasper_param_name
		if not frappe.flags.in_import:
			print "jasper reports autoname name {} parent {}".format(self.name, self.parent)
			self.name = self.parent + "_" + self.name

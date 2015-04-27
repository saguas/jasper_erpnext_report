# Copyright (c) 2013, Luis Fernandes and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import jasper_erpnext_report.core.JasperRoot as Jr
from jasper_erpnext_report.utils.utils import jaspersession_set_value



class JasperServerConfig(Document):
	def on_update(self):
		jaspersession_set_value("jasper_ignore_perm_roles", self.jasper_ignore_perm_roles)
		jaspersession_set_value("report_list_dirt_all", frappe.utils.now())
		jaspersession_set_value("report_list_dirt_doc", frappe.utils.now())

	def validate(self):
		frappe.local.jasper_session_obj = Jr.JasperRoot(self)
		frappe.local.jasper_session_obj.config()
		return True
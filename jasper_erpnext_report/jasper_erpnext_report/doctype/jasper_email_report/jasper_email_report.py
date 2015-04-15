# Copyright (c) 2013, Luis Fernandes and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
import os
from jasper_erpnext_report.utils.file import remove_directory

class JasperEmailReport(Document):

	def validate(self):
		if not self.jasper_email_report_name:
			raise frappe.PermissionError(_("You are not allowed to add this document."))

	def on_trash(self):
		if frappe.local.session['user'] == "Administrator":
			file_path = self.jasper_report_path
			if os.path.exists(file_path):
				root_path = file_path.rsplit("/",1)
				remove_directory(root_path[0])
			return True
		raise frappe.PermissionError(_("You are not allowed to remove this document."))

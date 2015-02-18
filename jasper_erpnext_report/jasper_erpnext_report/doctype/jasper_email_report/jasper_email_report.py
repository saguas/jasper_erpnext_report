# Copyright (c) 2013, Luis Fernandes and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class JasperEmailReport(Document):

	def validate(self):
		if not self.jasper_email_report_name:
			raise frappe.PermissionError(_("You are not allowed to add this doc"))

	def on_trash(self):
		if frappe.local.session['user'] == "Administrator":
			return True
		raise frappe.PermissionError(_("You are not allowed to remove this doc"))

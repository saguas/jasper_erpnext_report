from __future__ import unicode_literals
__author__ = 'luissaguas'

import frappe, os, jasper_erpnext_report, re
from frappe import _
from jasper_erpnext_report.utils.file import get_file, get_extension
no_cache = True

def get_context(context):

	if frappe.local.session['sid'] == 'Guest':
		return {"message":_("Please login first!"), "title":_("Not Permitted")}

	return {"message":_("Switch to Desk to see the list of emailed reports."), "title":_("Not Permitted")}



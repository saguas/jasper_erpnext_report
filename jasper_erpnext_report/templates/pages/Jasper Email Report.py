from __future__ import unicode_literals
__author__ = 'luissaguas'

import frappe
from frappe import _
no_cache = True

def get_context(context):

	if frappe.local.session['sid'] == 'Guest':
		return {"message":_("Please login first!"), "title":_("Not Permitted")}

	return {"message":_("Switch to Desk to see the list of emailed reports."), "title":_("Not Permitted")}



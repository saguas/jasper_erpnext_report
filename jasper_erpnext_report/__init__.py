from __future__ import unicode_literals
import frappe
import logging

jasper_session_obj = frappe.local("jasper_session_obj")
jasper_session = frappe.local("jasper_session")
pyjnius = False
jasperserverlib = False


frappe.get_logger("jasper_erpnext_report").addHandler(logging.NullHandler())

fds = frappe.local("fds")
batch = frappe.local("batch")

from .utils.utils import get_Frappe_Version
FRAPPE_VERSION = get_Frappe_Version()
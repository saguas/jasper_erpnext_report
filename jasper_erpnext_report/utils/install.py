from __future__ import unicode_literals
__author__ = 'saguas'

import frappe
import frappe.utils
from frappe.website import render, statics


def before_install():
	frappe.db.sql_ddl("""CREATE TABLE IF NOT EXISTS tabJasperSessions(
		user varchar(255) DEFAULT NULL,
		sessiondata longtext,
		lastupdate datetime(6) DEFAULT NULL,
		status varchar(20) DEFAULT NULL
		)""")

	frappe.db.sql_ddl("""CREATE TABLE IF NOT EXISTS tabJasperReqids(
		reqid varchar(255) DEFAULT NULL,
		data longtext,
		lastupdate datetime(6) DEFAULT NULL,
		KEY reqid (reqid)
		)""")

def after_install(rebuild_website=False):
	version = frappe.utils.cint(frappe.__version__.split(".", 1)[0])
	if version >= 5:
		return
	if rebuild_website:
		render.clear_cache()
		statics.sync().start()

	init_singles()
	frappe.db.commit()
	frappe.clear_cache()


def init_singles():
	singles = [single['name'] for single in frappe.get_all("DocType", filters={'issingle': True})]
	for single in singles:
		if not frappe.db.get_singles_dict(single):
			doc = frappe.new_doc(single)
			doc.ignore_mandatory=True
			doc.ignore_validate=True
			doc.save()
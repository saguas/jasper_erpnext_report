# Copyright (c) 2013, Luis Fernandes and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import logging
from frappe.model.document import Document
#from jasper_erpnext_report.core.jaspersession import JasperServerSession
#from jasper_erpnext_report.utils.utils import get_jasper_session_data_from_db, get_jasper_session_data_from_cache
#import json
import jasper_erpnext_report.core.JasperRoot as Jr
from jasper_erpnext_report.utils.utils import jaspersession_set_value

_logger = logging.getLogger(frappe.__name__)


class JasperServerConfig(Document):
	def on_update(self):
		jaspersession_set_value("jasper_ignore_perm_roles", self.jasper_ignore_perm_roles)
	def validate(self):
		frappe.local.jasper_session_obj = Jr.JasperRoot(self)#JasperServerSession(self)
		#frappe.local.jasper_session_obj.validate()
		frappe.local.jasper_session_obj.config()
		return True

"""
	def before_save(self, method=None):
		#data = get_session_data("jaspersession")
		jso = frappe.local.jasper_session_obj
		if jso.use_server():
			info = []
			#if doc.jasper_server_name don't start with { then already converted do nothing
			try:
				server_info = json.loads(jso.doc.jasper_server_name)
				for k,v in server_info.iteritems():
					info.append(k+": "+v)
				print "jso**************** server_info {}".format("\n".join(info))
				self.jasper_server_name = "\n".join(info)
			except:
				#save as string
				self.jasper_server_name = jso.doc.jasper_server_name
		else:
			self.jasper_server_name = ""
"""

"""def get_session_data(sessionId):
	data = get_jasper_session_data_from_cache(sessionId)
	if not data:
		rec = get_jasper_session_data_from_db()
		if rec:
			#print "rec: {0} expire date {1}".format(rec[0][1], get_expiry_period())
			data = frappe._dict(eval(rec and rec[0][1] or '{}'))
	else:
		data = frappe._dict({'data': data, 'user':data.user})
	#server_info = data['data'].get('jasper_server_name')
	print "server_info: {}".format(data)
	return data
"""
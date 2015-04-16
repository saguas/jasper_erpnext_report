from __future__ import unicode_literals
__author__ = 'luissaguas'

import frappe
import frappe.defaults
from frappe import _
from frappe.utils import cint


jasper_cache_data = [{"mcache":"jaspersession", "db": "tabJasperSessions"},{"mcache":'report_list_all', "db": None},
					{"mcache":'report_list_doctype', "db": None}]


def insert_jasper_list_all(data, cachename="report_list_all", tab="tabJasperReportListAll"):
		jaspersession_set_value(cachename, data)

def insert_list_all_memcache_db(data, cachename="report_list_all", tab="tabJasperReportListAll", fields={}):
	data['session_expiry'] = get_expiry_period(sessionId=cachename)
	data['last_updated'] = frappe.utils.now()
	for k,v in fields.iteritems():
		data[k] = v
	try:
		insert_jasper_list_all({"data":data}, cachename, tab)
	except:
		pass

def update_jasper_list_all(data, cachename="report_list_all", tab="tabJasperReportListAll"):
		# also add to memcache
		jaspersession_set_value(cachename, data)

def update_list_all_memcache_db(data, cachename="report_list_all", tab="tabJasperReportListAll", fields={}):
	data['session_expiry'] = get_expiry_period(sessionId=cachename)
	data['last_updated'] = frappe.utils.now()
	old_data = frappe._dict(jaspersession_get_value(cachename) or {})
	new_data = old_data.get("data", {})
	new_data.update(data)
	for k,v in fields.iteritems():
		new_data[k] = v
	update_jasper_list_all({"data":new_data}, cachename, tab)


def get_jasper_data(cachename, get_from_db=None, *args, **kargs):

		if frappe.local.session['sid'] == 'Guest':
			return None
		data = get_jasper_session_data_from_cache(cachename)
		if not data:
			data = get_jasper_data_from_db(get_from_db, *args, **kargs)
			if data:
				#if there is data in db but not in cache then update cache
				user = data.get("user")
				if user:
					d = frappe._dict({'data': data, 'user':data.get("user")})
				else:
					d = frappe._dict({'data': data})
				jaspersession_set_value(cachename, d)
		return data

def get_jasper_session_data_from_cache(sessionId):
		data = frappe._dict(jaspersession_get_value(sessionId) or {})
		if data:
			session_data = data.get("data", {})
			time_diff, expiry = get_jasper_session_expiry_seconds(session_data.get("last_updated"), session_data.get("session_expiry"))
			if time_diff > expiry:
				data = None

		return data and frappe._dict(data.data)

def get_jasper_session_expiry_seconds(last_update, session_expiry):
	time_diff = frappe.utils.time_diff_in_seconds(frappe.utils.now(),
		last_update)
	expiry = get_expiry_in_seconds(session_expiry)
	return time_diff, expiry


def get_jasper_data_from_db(get_from_db=None, *args, **kargs):
	if not get_from_db:
		rec = get_jasper_session_data_from_db()
	elif args:
		rec = get_from_db(*args)
	elif kargs:
		nargs = kargs.get("args", None)
		if nargs:
			rec = get_from_db(*nargs)
		else:
			rec = get_from_db(**kargs)
	else:
		rec = get_from_db()

	if rec:
		try:
			data = frappe._dict(eval(rec and rec[0][1] or '{}'))
		except:
			data = None
	else:
		data = None
	return data

def get_jasper_session_data_from_db():
	rec = frappe.db.sql("""select user, sessiondata
		from tabJasperSessions where
		TIMEDIFF(NOW(), lastupdate) < TIME("{0}") and status='Active'""".format(get_expiry_period("jaspersession")))
	return rec

def jaspersession_get_value(sessionId):
	return frappe.cache().get_value("jasper:" + sessionId)

def jaspersession_set_value(sessionId, data):
	frappe.cache().set_value("jasper:" + sessionId, data)

def delete_jasper_session(sessionId, tab="tabJasperSessions", where=None):

	frappe.cache().delete_value("jasper:" + sessionId)
	if tab and where:
		frappe.db.sql("""delete from {} where {}""".format(tab, where))
	elif tab:
		frappe.db.sql("""delete from {}""".format(tab))

	if tab:
		frappe.db.commit()

def get_expiry_in_seconds(expiry):
		if not expiry: return 3600
		parts = expiry.split(":")
		return (cint(parts[0]) * 3600) + (cint(parts[1]) * 60) + cint(parts[2])

def get_expiry_period(sessionId="jaspersession"):
	reports_names = ["report_list_doctype", "report_list_all"]
	if sessionId in reports_names:
		exp_sec = "24:00:00"
	elif "intern_reqid_" in sessionId or "local_report_" in sessionId:
		exp_sec = "8:00:00"
	elif "client_html_" in sessionId:
		exp_sec = "00:10:00"
	else:
		exp_sec = frappe.defaults.get_global_default("jasper_session_expiry") or "12:00:00"

		#incase seconds is missing
		if len(exp_sec.split(':')) == 2:
			exp_sec = exp_sec + ':00'
	return exp_sec

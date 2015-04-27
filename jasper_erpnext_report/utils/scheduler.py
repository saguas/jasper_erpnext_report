__author__ = 'luissaguas'
import frappe
from frappe import _
from jasper_erpnext_report.utils.utils import jasper_cache_data, delete_jasper_session, jaspersession_get_value,\
	get_expiry_in_seconds, get_jasper_session_expiry_seconds, get_expiry_period
from jasper_erpnext_report.utils.file import remove_directory


#call from bench frappe --python session or
#to be called from terminal: bench frappe --execute jasper_erpnext_report.utils.scheduler.list_all_memcached_keys_v4
def list_all_memcached_keys_v4(value=None):
	from memcache_stats import MemcachedStats
	memc = MemcachedStats()
	if value:
		for m in memc.keys():
			if value in m:
				print m
	else:
		print (memc.keys())

#to be called from terminal: bench frappe --execute jasper_erpnext_report.utils.scheduler.clear_all_jasper_cache_v4 to force clear cache
def clear_all_jasper_cache_v4(force=True):
	from memcache_stats import MemcachedStats
	#use memcache_stats for delete any cache that remains
	memc = MemcachedStats()
	for m in memc.keys():
		if "jasper" in m:
			value = m.split(":", 1)
			frappe.cache().delete_value(value[1])

#to be called from terminal: bench frappe --execute jasper_erpnext_report.utils.scheduler.clear_all_jasper_user_cache_v4 to force clear cache
def clear_all_jasper_user_cache_v4(force=True):
	from memcache_stats import MemcachedStats
	removed = 0
	#use memcache_stats for delete any cache that remains
	memc = MemcachedStats()
	for m in memc.keys():
		if "jasper:user" in m:
			if force:
				#remove site from key
				value = m.split(":", 1)
				frappe.cache().delete_value(value[1])
				removed += 1
			else:
				#remove jasper from key
				value = m.split(":", 1)
				v = value[1].split(":", 1)
				deleted = _f(v[1])
				if deleted:
					frappe.cache().delete_value(value[1])
					removed += 1
	if removed == 0:
		print _("No user cache was removed.")
	else:
		print _("was removed %s user cache(s)".format(removed))
	return removed


def clear_all_jasper_sessions():
	"""This effectively logs out all users"""
	for session in jasper_cache_data:
		delete_jasper_session(session.get("mcache"), tab=session.get("db"))


def clear_jasper_list():
	frappe.cache().delete_value("jasper:report_list_all")
	frappe.cache().delete_value("jasper:report_list_doctype")


#remove the files in compiled directory
#from command line remove and don't check expire time
#from scheduler remove only if past expire time
def clear_all_jasper_reports(force=True):
	deleted = force
	compiled_removed = 0
	emailed_removed = 0
	#to every intern_reqid is one local_report_ or from server?(to check)
	tabReqids = frappe.db.sql("select * from tabJasperReqids where reqid like 'intern_reqid_%'", as_dict=True)
	import ast
	from jasper_erpnext_report.utils.jasper_email import get_email_pdf_path

	for m in tabReqids:
		d = m.get('data')
		req = ast.literal_eval(d)
		reqId = req.get("reqids")[0][0]
		if not force:
			deleted = _f(reqId)

		if deleted:
			try:
				if "local_report_" not in reqId:
					continue

				intern_reqid = m.get("reqid")
				data = jaspersession_get_value(reqId)
				file_path = data['data'].get('result').get("uri").rsplit("/",1)
				compiled_path = file_path[0]
				#file_name = file_path[1]
				remove_directory(compiled_path)
				compiled_removed += 1
				#if this report was not sent by email then remove it from assets/jasper_erpnext_report/reports/
				urlemails = frappe.db.sql("""select count(*) from `tabJasper Email Report` where jasper_report_path like '%{0}%'""".format(intern_reqid))
				if not urlemails[0][0]>0:
					report_name = data['data'].get("report_name").get("data").get("report_name")
					db = req.get("db")
					path = get_email_pdf_path(report_name, intern_reqid, db)
					remove_directory(path)
					emailed_removed += 1

			except:
				print "Path does not exist!"

			frappe.cache().delete_value("jasper:" + reqId)
			frappe.cache().delete_value("jasper:" + intern_reqid)
			frappe.db.sql("""delete from tabJasperReqids where reqid in ('%s', '%s')"""%(reqId, intern_reqid))

			frappe.db.commit()

	if compiled_removed > 0:
		print _("Was removed {0} file(s) from compiled path and {1} file(s) from reports path (emailed only).".format(compiled_removed, emailed_removed))
	else:
		print _("No file was removed.")

def _f(sessionId):
	data = jaspersession_get_value(sessionId)
	deleted = False
	d = data.get('data') if data else {}
	if d:
		now = frappe.utils.now()
		last_updated = d['last_updated']
		time_diff = frappe.utils.time_diff_in_seconds(now, last_updated) if last_updated else 0
		expire = get_expiry_in_seconds(d['session_expiry'])
		if  time_diff > expire:
			deleted = True
	return deleted

def clear_expired_jasper_sessions():
	"""This function is meant to be called from scheduler"""
	removed = 0
	for sessionId in jasper_cache_data:
		sid = sessionId.get("mcache")
		deleted = _f(sid)
		if deleted:
			frappe.cache().delete_value("jasper:" + sid)
			removed += 1
			db = sessionId.get("db")
			if db:
				frappe.db.sql("""delete from `%s` where reqid='%s'"""%(db, sid,))

	clear_all_jasper_reports(force=False)
	version = frappe.utils.cint(frappe.__version__.split(".", 1)[0])
	if version < 5:
		r = clear_all_jasper_user_cache_v4(force=False)
		removed += r

	frappe.db.commit()

	if removed == 0:
		print _("No goblal jasper cache was removed.")
	else:
		print _("was removed %s global jasper cache(s)".format(removed))

	return removed

"""
#remove from disc all reports that expired based on timestamp of html file
def clear_expired_jasper_html():
	import os, jasper_erpnext_report
	from datetime import datetime
	path_jasper_module = os.path.dirname(jasper_erpnext_report.__file__)
	path = os.path.join(path_jasper_module, "public", "reports")
	rootDir = path
	for dirName, subdirList, fileList in os.walk(rootDir, topdown=False):
		for fname in fileList:
			names = fname.split(".")
			tam = len(names)
			if tam > 1:
				ext = names[tam - 1]
				if ext == "html":
					last_modified = os.path.getmtime(os.path.join(dirName,fname))
					lm = datetime.fromtimestamp(last_modified).strftime('%Y-%m-%d %H:%M:%S')
					texpire = get_expiry_period("client_html_")
					time_diff, expiry = get_jasper_session_expiry_seconds(lm, texpire)
					if time_diff > expiry:#remove from disc
						remove_directory(dirName)
"""

#to be called from terminal: bench frappe --execute jasper_erpnext_report.utils.scheduler.clear_jasper to force clear cache
def clear_jasper():
	#local_session_data = frappe.local.session
	clear_cache()

def clear_cache():
	"""hook: called from terminal bench frappe --clear_cache, only clear session if past 24 hours"""
	local_session_data = frappe.local.session
	if local_session_data.sid == "Administrator":
		clear_all_jasper_sessions()
		clear_all_jasper_cache_v4()
		clear_all_jasper_reports()


#version = frappe.utils.cint(frappe.__version__.split(".", 1)[0])
#if version < 5:
__author__ = 'luissaguas'
import frappe
from frappe import _
from jasper_erpnext_report.utils.utils import jaspersession_get_value,\
	get_expiry_in_seconds, get_jasper_data, get_expiry_period, get_jasper_session_expiry_seconds
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


def list_all_redis_keys(key):
	redis = frappe.cache()
	return redis.get_keys(key)

#to be called from terminal: bench frappe --execute jasper_erpnext_report.utils.scheduler.clear_all_jasper_cache_v4 to force clear cache
def clear_all_jasper_from_cache_v4():
	from memcache_stats import MemcachedStats
	#use memcache_stats for delete any cache that remains
	memc = MemcachedStats()
	for m in memc.keys():
		if "jasper" in m:
			value = m.split(":", 1)
			frappe.cache().delete_value(value[1])

def clear_all_jasper_from_redis_cache(key="jasper"):
	redis = frappe.cache()
	redis.delete_keys(key)
	print _("Was removed keys with pattern {0}* from redis cache".format(key))

def clear_all_jasper_user_redis_cache(force=True):
	removed = 0
	if force:
		clear_all_jasper_from_redis_cache("jasper:user")
		print _("Was removed by force jasper:user* pattern from redis cache")
		return 1
	else:
		redis = frappe.cache()
		keys = redis.get_keys("jasper:user")
		for key in keys:
			if check_if_expire(key):
				redis.delete_value(key)
				removed += 1

	print _("Was removed {0} user(s) from redis cache".format(removed))

	return removed

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
				deleted = check_if_expire(v[1])
				if deleted:
					frappe.cache().delete_value(value[1])
					removed += 1
	if removed == 0:
		print _("No user cache was removed.")
	else:
		print _("Was removed {0} user cache(s)".format(removed))
	return removed


def check_if_expire(reqId):
	req = jaspersession_get_value(reqId)
	if not req:
		return False
	data = req.get("data", {})
	last_updated = data.get("last_updated", frappe.utils.now())
	session_expire = req.get("session_expiry", "00:00:00")
	time_diff, expire = get_jasper_session_expiry_seconds(last_updated, session_expire)
	if time_diff >= expire:
		return True

	return False

def clear_jasper_list(force=True):
	removed = 0
	if force:
		frappe.cache().delete_value("jasper:report_list_all")
		frappe.cache().delete_value("jasper:report_list_doctype")
		return 2

	if check_if_expire("report_list_all"):
		frappe.cache().delete_value("jasper:report_list_all")
		removed += 1

	if check_if_expire("report_list_doctype"):
		frappe.cache().delete_value("jasper:report_list_doctype")
		removed += 1

	return removed


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
		data = jaspersession_get_value(reqId)
		if not force:
			deleted = _f(data)

		if deleted:
			try:
				if "local_report_" not in reqId:
					continue

				intern_reqid = m.get("reqid")
				if not data:
					data = frappe.db.sql("select * from tabJasperReqids where reqid='{0}'".format(reqId), as_dict=True)
					print "go to db data {}".format(data)
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

def _f(data):
	deleted = False

	if data is None or isinstance(data, basestring):
		return True

	d = data.get('data') if data else {}
	if d:
		now = frappe.utils.now()
		last_updated = d['last_updated']
		time_diff = frappe.utils.time_diff_in_seconds(now, last_updated) if last_updated else 0
		expire = get_expiry_in_seconds(d['session_expiry'])
		if  time_diff > expire:
			deleted = True
	return deleted

def clear_all_jasper_cache(force=True):
	"""This function is meant to be called from scheduler"""
	removed = 0

	version = frappe.utils.cint(frappe.__version__.split(".", 1)[0])
	if version > 4:
		r = clear_all_jasper_user_redis_cache(force=force)
		removed += r
	else:
		r = clear_all_jasper_user_cache_v4(force=force)
		removed += r

	clear_jasper_list(force=force)
	removed += clear_jasper_sessions(force=force)
	frappe.db.commit()

	if removed == 0:
		print _("No goblal jasper cache was removed.")
	else:
		print _("Was removed {0} global jasper cache(s)".format(removed))

	return removed

def clear_expired_jasper_reports(force=False):
	clear_all_jasper_reports(force=force)

def clear_expired_jasper_sessions(force=False):
	clear_all_jasper_cache(force=force)


def clear_jasper_sessions(force=True):
	removed = 0
	sid = "jaspersession"
	deleted = force
	data = get_jasper_data(sid)
	if not data:
		return removed

	if not force:
		deleted = _f(data)
	if deleted:
		frappe.cache().delete_value("jasper:" + sid)
		removed += 1
		frappe.db.sql("""delete from `tabJasperSessions` """)
		if force:
			version = frappe.utils.cint(frappe.__version__.split(".", 1)[0])
			if version > 4:
				clear_all_jasper_from_redis_cache()
			else:
				clear_all_jasper_from_cache_v4()

		print _("was removed {0} jaspersession(s)".format(removed))

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


def clear_expired(force=False):
	clear_expired_jasper_reports(force=force)
	clear_expired_jasper_sessions(force=force)

#to be called from terminal: bench frappe --execute jasper_erpnext_report.utils.scheduler.clear_jasper to force clear cache
def clear_jasper():
	#local_session_data = frappe.local.session
	clear_cache()

def clear_cache():
	"""hook: called from terminal bench frappe --clear_cache, only clear session if past 24 hours"""
	local_session_data = frappe.local.session
	if local_session_data.sid == "Administrator":
		clear_all_jasper_reports()
		clear_all_jasper_cache()
		version = frappe.utils.cint(frappe.__version__.split(".", 1)[0])
		if version > 4:
			clear_all_jasper_from_redis_cache()
		else:
			clear_all_jasper_from_cache_v4()


#version = frappe.utils.cint(frappe.__version__.split(".", 1)[0])
#if version < 5:
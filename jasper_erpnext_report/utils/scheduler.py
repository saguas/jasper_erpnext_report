__author__ = 'luissaguas'
import frappe, logging
from memcache_stats import MemcachedStats
from jasper_erpnext_report.utils.utils import jasper_cache_data, delete_jasper_session, jaspersession_get_value, get_expiry_in_seconds, get_jasper_session_expiry_seconds, get_expiry_period
from jasper_erpnext_report.utils.file import remove_directory, get_jasper_path, remove_compiled_report
#import jasper_erpnext_report


_logger = logging.getLogger(frappe.__name__)

#call from bench frappe --python session
def list_all_memcached_keys(value):
	memc = MemcachedStats()
	if value:
		for m in memc.keys():
			if value in m:
				print m
	else:
		print (memc.keys())

#call from bench frappe --python session
def get_memcache_value(value):
	memc = MemcachedStats()
	print memc.getValue(value)

def clear_all_jasper_sessions():
	"""This effectively logs out all users"""
	#frappe.only_for("Administrator")
	for session in jasper_cache_data:
		delete_jasper_session(session.get("mcache"), tab=session.get("db"))
	
def clear_jasper_list():
	delete_jasper_session("report_list_all", tab="tabJasperReportListAll")
	delete_jasper_session("report_list_doctype", tab="tabJasperReportListDoctype")

def clear_all_jasper_reports(force=True):
	#rec = frappe.db.sql("""select reqid from tabJasperReqids""")
	#if rec:
	#	for r in rec:
	#		reqId = r[0]
	#		delete_jasper_reqid_data(reqId)
	#use memcache_stats for delete any cache that remains
	deleted = force
	memc = MemcachedStats()
	for m in memc.keys():
		#if "local_report" in m or "intern_reqid" in m:
		if "jasper" in m:
			reqId = m.split(":")
			print "reqId %s" % reqId
			#print "reqiId {}".format(data)
			if not force:
				deleted = _f(reqId[2])

			if deleted:
				frappe.cache().delete_value("jasper:" + reqId[2])
				frappe.db.sql("""delete from tabJasperReqids where reqid='%s'"""%(reqId[2],))
				#first do not call for all sites, but if do not exists try all sites
				#jasper_path = get_jasper_path(True)
				#compiled_path = get_compiled_path(jasper_path, reqId[2][13:])#remove "local_report_" from reqId
				#print "compiled_path {}".format(compiled_path)
				try:
					data = jaspersession_get_value(reqId[2])
					compiled_path = data['data'].get('path')
					file_name = data['data'].get('fileName')
					#print "to delete {}".format(compiled_path.replace(file_name,""))
					remove_directory(compiled_path.replace(file_name,""))
				except:
					print "Path does not exist!"

	if force:
		#clean orphans in db
		frappe.db.sql("""delete from tabJasperReqids""")
		#clean all local reports
		for e in [True, False]:
			jasper_path = get_jasper_path(e)
			remove_compiled_report(jasper_path)

	print (memc.keys())

def _f(sessionId):
	data = jaspersession_get_value(sessionId)
	#data = get_jasper_data(sessionId, )
	deleted = False
	d = data.get('data') if data else {}
	if d:
		now = frappe.utils.now()
		last_updated = d['last_updated']
		time_diff = frappe.utils.time_diff_in_seconds(now, last_updated) if last_updated else 0
		expire = get_expiry_in_seconds(d['session_expiry'])
		if  time_diff > expire:
			#delete_jasper_session(sessionId, tab=dbId)
			deleted = True
	return deleted

def clear_expired_jasper_sessions():
	"""This function is meant to be called from scheduler"""
	print "Clear expired jasper sessions"
	for sessionId in jasper_cache_data:
		deleted = _f(sessionId.get("mcache"))
		if deleted:
			frappe.cache().delete_value("jasper:" + sessionId.get("mcache"))
			frappe.db.sql("""delete from `%s` where reqid='%s'"""%(sessionId.get("db"), sessionId.get("mcache"),))
	#frappe.db.sql("""delete from tabJasperSessions where TIMEDIFF(NOW(), lastupdate) > TIME("{0}")""".format(get_expiry_period()))
	clear_all_jasper_reports(force=False)
	frappe.db.commit()

#remove from disc all reports that expired based on timestamp of html file
def clear_expired_jasper_html():
	import os, jasper_erpnext_report
	from datetime import datetime
	path_jasper_module = os.path.dirname(jasper_erpnext_report.__file__)
	path = os.path.join(path_jasper_module, "public", "reports")
	rootDir = path
	print "path {}".format(path)
	for dirName, subdirList, fileList in os.walk(rootDir, topdown=False):
		print('Found directory: %s' % dirName)
		for fname in fileList:
			print('\t%s' % fname)
			names = fname.split(".")
			tam = len(names)
			if tam > 1:
				ext = names[tam - 1]
				if ext == "html":
					last_modified = os.path.getmtime(os.path.join(dirName,fname))
					lm = datetime.fromtimestamp(last_modified).strftime('%Y-%m-%d %H:%M:%S')
					texpire = get_expiry_period("client_html_")
					print "last_modified {} texpire {}".format(last_modified, texpire)
					time_diff, expiry = get_jasper_session_expiry_seconds(lm, texpire)
					if time_diff > expiry:#remove from disc
						remove_directory(dirName)

#to be called from terminal: bench frappe --execute jasper_erpnext_report.utils.scheduler.clear_jasper to force clear cache
def clear_jasper():
	local_session_data = frappe.local.session
	print "\n\njasperserver clear_cache called {}\n".format(local_session_data)
	clear_cache()

def clear_cache():
	"""hook: called from terminal bench frappe --clear_cache, only clear session if past 24 hours"""
	#last_updated = jaspersession_get_value("jasper_clear_cache_time")
	#now = frappe.utils.now()
	#if not last_updated:
	#	jaspersession_set_value("jasper_clear_cache_time", now)
	local_session_data = frappe.local.session
	if local_session_data.sid == "Administrator":
		#time_diff = frappe.utils.time_diff_in_hours(now, last_updated) if last_updated else 0
		print "clear_cache {}".format(local_session_data)
		_logger.info("jasperserver clear_cache called {}".format(local_session_data))
		#if time_diff > 24 or force:
		#_logger.info("jasperserver clear_cache called {}, time past since last clear is {}".format(local_session_data, time_diff))
		frappe.cache().delete_value("jasper:" + "report_list_dirt_all")
		frappe.cache().delete_value("jasper:" + "report_list_dirt_doc")
		clear_all_jasper_sessions()
		clear_all_jasper_reports()
		clear_expired_jasper_html()
		clear_jasper_list()
		frappe.db.commit()
		#jaspersession_set_value("jasper_clear_cache_time", now)

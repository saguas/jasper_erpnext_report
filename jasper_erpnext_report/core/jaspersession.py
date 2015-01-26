from __future__ import unicode_literals
import logging, os
from urllib2 import unquote
import inspect

import jasperserver.core as jasper
from jasperserver.repo_search import Search
from jasperserver.resource_details import Details
from jasperserver.resource_download import DownloadBinary
#from jasperserver.report import Report
#from jasperserver.core.reportingService import ReportingService
#from jasperserver.core.ReportExecutionRequest import ReportExecutionRequest
from jasperserver.core.exceptions import Unauthorized, NotFound

from io import BytesIO
from PyPDF2 import PdfFileMerger
import StringIO

from jasper_erpnext_report.utils.file import get_query, get_params
from jasper_erpnext_report.utils.report import Report, prepareCollectResponse, get_jasper_reqid_data, update_jasper_reqid_record
from jasper_erpnext_report.jasper_reports.run_local_report import jasper_run_local_report, getLocalReport, getLocalPolling
from jasper_erpnext_report import jasper_session_obj


import json
import zipfile

from frappe import _
import frappe
import frappe.utils
from frappe.model.document import Document
import jasper_erpnext_report.utils.utils as utils
"""from jasper_erpnext_report.utils.utils import validate_print_permission, jaspersession_get_value,\
	jaspersession_set_value, delete_jasper_session, check_jasper_perm, jasper_report_names_from_db,\
	do_doctype_from_jasper, import_all_jasper_remote_reports, get_expiry_period, get_jasper_data,\
	insert_list_all_memcache_db, update_list_all_memcache_db, check_jasper_doc_perm, call_hook_for_param
"""
#from requests.adapters import ConnectionError
jasper_fields_not_supported = ["parent", "owner", "modified_by", "parenttype", "parentfield", "docstatus", "doctype", "name", "idx"]

_logger = logging.getLogger(frappe.__name__)

'''
Decorator Handle timeout jasperserver. 
If timeout catch exception Unauthorized and call timeout().
And after sucessfuly login call again a function
'''
def _jasperserver(fn):
	"""
	decorator for jasperserver functions
	"""
	def innerfn(*args, **kwargs):
		newargs = {}
		me = args[0]
		#if me.doc and me.doc.use_jasper_server == "None":
		#	return
		try:
			fnargs, varargs, varkw, defaults = inspect.getargspec(fn)
			for a in fnargs:
				if a in kwargs:
					newargs[a] = kwargs.get(a)
			
			me.resume()
			_logger.info("innerfn JasperServerSession {}".format(me.data))
			if me.data['data']:
				#if not me.doc:
				#	me.doc = me.data['data']
				#me.update()
				if me.use_server():
					me.session = frappe.local.jasper_session = jasper.session(me.doc.get("jasper_server_url"), resume=True)
					me.session.resume(me.data['data']['cookie'])
			else:
				#only one should make login
				me._login()
			#only used by methods that connect to jasper server
			if me.use_server() and not me.in_jasper_session():
				_logger.info("innerfn JasperServerSession not in jasper sesssion {} *************************".format(me.session.session.getSessionId()))
				#return
				frappe.msgprint(_("Jasper Server is down. Please ask the administrator to check jasperserver or change to local report only (you will need pyjnius)."))
			fn_result = fn(*args, **newargs)
			me.update()
			frappe.local.jasper_session_obj = me
			return fn_result
			#_logger.info("Decorator _jasperserver args {0} newargs {1}".format(args, newargs))
			
		except Unauthorized, e:
			_logger.info("************************Decorator _jasperserver error {2} args {0} newargs {1}".format(args, newargs, e))
			args[0]._timeout()
			if me.in_jasper_session():
				fn_result = fn(*args, **newargs)
				me.update()
				utils.jaspersession_set_value("last_jasper_session_timeout", frappe.utils.now())
				return fn_result
		#finally:
		#	if me.use_server() and not me.in_jasper_session():
		#		return
			#fn_result = fn(*args, **newargs)
		#	me.update()
		#	return fn_result
		

	return innerfn

class JasperServerSession(object):

	def __init__(self, doc={}):
		if isinstance(doc, Document):
			self.doc = frappe._dict(doc.as_dict())
		else:
			self.doc = frappe._dict(doc)
		local_session_data = frappe.local.session
		self.user = local_session_data["user"]
		self.sid = local_session_data["sid"]
		self.reset_data_session()
		#_logger.info("__init__ JasperServerSession {0} self.data? {1}".format(frappe.local.session, not self.data['data']))

	def reset_data_session(self):
		self.data = frappe._dict({'data': frappe._dict({})})
		self.session = frappe.local.jasper_session = frappe._dict({'session': frappe._dict({})})

	def use_server(self):
		if not self.doc:
			print "use_server not self.doc"
			self.resume()
			if not self.data["data"]:
				self._login()
		#print "use_jasper_server {}".format(self.doc.use_jasper_server)
		doc_jasper_server = self.doc.use_jasper_server.lower()
		return doc_jasper_server == "jasperserver only" or doc_jasper_server == "both"
		#pass

	def in_jasper_session(self):
		return self.session.session.getSessionId()

	def use_local(self):
		if not self.doc:
			self.resume()
			if not self.data["data"]:
				self._login()
		#print "use_jasper_server {}".format(self.doc.use_jasper_server)
		doc_jasper_server = self.doc.use_jasper_server.lower()
		return doc_jasper_server == "local jrxml only" or doc_jasper_server == "both"

	def use_local_server(self):
		return self.use_local() and self.use_server()

	def get_report_origin(self):
		if not self.doc:
			self.resume()
			if not self.data["data"]:
				self._login()
		return self.doc.use_jasper_server.lower()

	def _login(self):
		#try:
		self._createJasperSession()
		#except:
		#	_logger.info("_login: JasperServerSession Error while login")
	#called if use jasperserver: check if any connection value have changed
	def must_connect(self):
		conn = False
		#if we have no data we must connect to get cookie
		if not self.data["data"]:
			return True
		#check if we are changing from local to server
		if self.doc.use_jasper_server != self.data["data"].get('use_jasper_server') or not self.data["data"]["cookie"]:
			self.reset_data_session()
			self.delete_jasper_session()
			return True

		jasper_login_data = ['jasper_username', 'jasper_server_url', 'jasper_server_password', 'jasper_report_root_path']
		for key,value in self.data["data"].iteritems():
			if key in jasper_login_data:
				if self.doc.get(key) != value or not value:
					conn = True
					break
		return conn

	def validate(self):
		if self.use_local() and not self.use_server():
			return self.update_cache()
		jasper_login_data = ['jasper_username', 'jasper_server_url', 'jasper_server_password', 'jasper_report_root_path']
		for key,value in self.doc.iteritems():
			if key in jasper_login_data and not value:
				frappe.msgprint(_("Please the field (%s) can't be empty.") % (key),
					raise_exception=True)
		return self.update_cache()

	def update_cache(self):
		#if not request from browser no doc yet. Not from browser use login
		#jasper_report_import = False
		_logger.info("JasperServerSession update_cache self.doc {}".format(self.doc))
		if not self.doc:
			return
		from jasper_erpnext_report import pyjnius
		if self.use_local() and not pyjnius:
			frappe.throw(_("You don't have local server. Install pyjnius first.!!!" ))

		if self.use_server():
			self.resume()
			if not self.must_connect():
				#save to memcache and db
				print "************** no need to connect!!!"
				self.session = frappe.local.jasper_session = jasper.session(self.doc.get("jasper_server_url"), resume=True)
				self.session.resume(self.data['data']['cookie'])
				if self.doc.import_all_reports: #and not self.data['data'].get('import_all_reports'):
					self.import_all_jasper_reports(self.doc)
				return self.update(force_cache=True, force_db=True)
			#there are changes but we probably are connected, if there is a cookie!
			if self.data["data"] and self.in_jasper_session():
				_logger.info("JasperServerSession update_cache go to logout {}".format(self.data))
				self._logout()
			#first invalidate memcache and db. All users must be disconnected.
			#self.delete_jasper_session()
			self._login()
			if self.doc.import_all_reports:
				self.import_all_jasper_reports(self.doc)
			self.doc.jasper_server_name = self._get_server_info()
			self.data['data']['jasper_server_name'] = self.doc.jasper_server_name
			self.update(force_db=True)
			#frappe.db.sql("update tabSingles set value='%s' where doctype='%s' and field='%s'" % (server_info, "JasperServerConfig", "jasper_server_name"))
			#frappe.db.commit()
			#print "server_info: {}".format(self.doc.jasper_server_name)
			return

		#here, just Local jasperreport
		#check if session exist, if not login
		self.resume()
		if self.data["data"]:
			self.update(force_cache=True, force_db=True)
		else:
			#delete all db old sessions if exist
			self.delete_jasper_session()
			self._login()

		return
		#_logger.info("JasperServerSession start after login self.data {}".format(self.data))
	
	def _logout(self):
		if not self.use_server():
			return
		cookie = self.data['data'].get("cookie")
		if not cookie:
			self.reset_data()
			self.delete_jasper_session()
			return
		url = self.data['data'].get("jasper_server_url")
		session = jasper.session(url, resume=True)
		session.resume(cookie)
		session.logout()
		#frappe.db.begin()
		self.reset_data_session()
		self.delete_jasper_session()
		frappe.db.commit()
		
		#_logger.info("jasperserver is logout {} sid {}".format(self.data['data'].get('jasper_server_url'), self.sid))
		
	def _timeout(self):
		#self._connect()
		#self._createJasperSession()
		try:
			self._login()
		except:
			_logger.info("_login: JasperServerSession Error while timeout and login")

		#set all db rows to status="timeout"
		#self.data['data']['cookie'] = frappe.local.jasper_session.session.getSessionId()
		#update_in_db = self.update(force_db=True)
		_logger.info("_timeout JasperServerSession login successfuly {0}".format(self.doc))
		
	def _connect(self):
		try:
			if not self.doc:
				#self.doc = frappe.db.get_value('JasperServerConfig', None, ['jasper_username', 'jasper_server_password', 'jasper_server_url','jasper_report_root_path'], ignore=True, as_dict=True)
				self.doc = frappe.db.get_value('JasperServerConfig', None, "*", ignore=True, as_dict=True)

			#self.session = frappe.local.jasper_session = frappe._dict({'session': frappe._dict({})})

			if self.use_server():
				self.session = frappe.local.jasper_session = jasper.session(self.doc.jasper_server_url, self.doc.jasper_username, self.doc.jasper_server_password)

		except Exception as e:
			_logger.info("jasperserver login error {0}")
			frappe.msgprint(_("JasperServer login error, reason: {}".format(e)))
	
	def _createJasperSession(self):
		
			self._connect()

			#print "self.session {}".format(self.session)
			
			if self.user!="Guest": #and self.session:
				self.update_data_cache()
				self.data['data']['session_expiry'] = utils.get_expiry_period()
				self.insert_jasper_session_record()
				frappe.db.commit()
		
	def insert_jasper_session_record(self):
		frappe.db.sql("""insert into tabJasperSessions
			(sessiondata, user, lastupdate, status)
			values (%s , %s, NOW(), 'Active')""",
				(str(self.data['data']), self.data['user']))
		# also add to memcache
		utils.jaspersession_set_value("jaspersession", self.data)
		utils.jaspersession_set_value("last_db_jasper_session_update", frappe.utils.now())

	def update_data_cache(self):
		doc = self.doc
		#if isinstance(self.doc, Document):
		#	doc = frappe._dict(self.doc.as_dict())
		self.data['data'] = {letter: i for letter,i in doc.iteritems() if letter not in jasper_fields_not_supported}
		self.data['data']['cookie'] = frappe.local.jasper_session.session.getSessionId() if frappe.local.jasper_session.session else {}
		self.data['user'] = self.user
		self.data['data']['last_updated'] = frappe.utils.now()
		print "update_data_cache {}".format(self.data)

	def resume(self):
		if self.data['data']:
			return
		data = self.get_jasper_session_data()
		if data:
			#self.data = frappe._dict({'data': data, 'user':data.user, 'sid': self.sid})
			self.data = frappe._dict({'data': data, 'user':data.get("user")})
			if not self.doc:
				self.doc = self.data['data']
		
		_logger.info("JasperServerSession on resume {}".format(self.data))
	
	def get_jasper_session_data(self):
		#if self.sid=="Guest":
		#	return None

		data = utils.get_jasper_data("jaspersession")

		if not data:
			self.delete_jasper_session()
		"""data = self.get_jasper_session_data_from_cache()
		if not data:
			data = self.get_jasper_session_data_from_db()
		#return data
		if data:
			data = frappe._dict(data)"""

		return data
	
	"""def get_jasper_session_data_from_cache(self):
		return get_jasper_session_data_from_cache("jaspersession")

	def get_jasper_session_data_from_db(self):
		rec = get_jasper_session_data_from_db()
		if rec:
			#print "rec: {0} expire date {1}".format(rec[0][1], get_expiry_period())
			data = frappe._dict(eval(rec and rec[0][1] or '{}'))
			data.user = rec[0][0]
		else:
			self.delete_jasper_session()
			data = None

		return data"""
		
	def delete_jasper_session(self):
		utils.delete_jasper_session("jaspersession")
		#frappe.db.commit()
		
	
	def update(self, force_cache=False, force_db=False):
		"""extend session expiry"""
		if (frappe.session['user'] == "Guest"):
			return

		now = frappe.utils.now()

		if force_cache:
			self.update_data_cache()
		else:
			self.data['data']['last_updated'] = now

		# update session in db
		#last_updated = frappe.cache().get_value("last_db_jasper_session_update:" + self.sid)
		last_updated = utils.jaspersession_get_value("last_db_jasper_session_update")
		time_diff = frappe.utils.time_diff_in_seconds(now, last_updated) if last_updated else None

		# database persistence is secondary, don't update it too often
		updated_in_db = False
		if force_db or (time_diff==None) or (time_diff > 300):
		#if force_db:
			frappe.db.sql("""update tabJasperSessions set sessiondata=%s,
				lastupdate=NOW() where TIMEDIFF(NOW(), lastupdate) < TIME(%s) and status='Active'""" , (str(self.data['data']), utils.get_expiry_period()))
			#frappe.cache().set_value("last_db_jasper_session_update:" + self.sid, now)
			utils.jaspersession_set_value("last_db_jasper_session_update", now)
			updated_in_db = True

		# set in memcache
		#print "memcache save {}".format(self.data)
		utils.jaspersession_set_value("jaspersession", self.data)

		return updated_in_db
	
	@_jasperserver		
	def get_reports_list_from_server2(self, force=False):
			ret = {}
			#if self.in_jasper_session():
			s = Search(self.session)
			result = s.search(path=self.doc.get("jasper_report_root_path"), type="reportUnit")
			reports = result.getDescriptor().json_descriptor()
			for report in reports:
				ics = []
				d = Details(self.session, report.get("uri"))
				r_details = d.details()
				r_param = r_details.getDescriptor().json_descriptor()
				#_logger.info("jasperserver get_reports_list_from_server {}".format(r_param[0].get('queryString')))
				#print "reports:: {}".format(r_param[0].get('jrxml').get('jrxmlFile').get('uri'))
				#query = self.get_query_jrxmlFile_from_server(r_param[0].get('jrxml').get('jrxmlFile').get('uri'))
				query=""
				for ic in r_param[0].get("inputControls",[]):
					ics.append(ic.get("inputControl", []))
				updateDate = report.get("updateDate", None)
				if not updateDate:
					updateDate = report.get("creationDate", frappe.utils.now())
				print "inputcontrols {} ************************************".format(ics)
				ret[report.get("label")] = {"uri":report.get("uri"), "inputControls": ics, "updateDate": updateDate, "queryString": query}

			return ret

	def _get_reports_list_from_server(self, force=False):
		ret = {}
		#if self.in_jasper_session():
		s = Search(self.session)
		result = s.search(path=self.doc.get("jasper_report_root_path"), type="reportUnit")
		reports = result.getDescriptor().json_descriptor()
		for report in reports:
			ics = []
			d = Details(self.session, report.get("uri"))
			r_details = d.details(expanded=False)
			r_param = r_details.getDescriptor().json_descriptor()
			#_logger.info("jasperserver get_reports_list_from_server {}".format(r_param[0].get('queryString')))
			#print "reports:: {}".format(r_param[0].get('jrxml').get('jrxmlFile').get('uri'))
			uri = r_param[0].get('jrxml').get('jrxmlFileReference').get('uri')
			#print "uri???????????????????? %s" % uri
			file_content = self.get_jrxml_from_server(uri)
			params = get_params(BytesIO(file_content))
			query = self.get_query_jrxmlFile_from_server(file_content)
			for param in params:
				pname = param.xpath('./@name')
				pclass = param.xpath('./@class')
				ptype = pclass[0].split(".")
				c = len(ptype) - 1
				ics.append({"label":pname[0], "type":ptype[c].lower()})
				#print "params **************** {0} report.get(label) {1}".format(pname[0], report.get("label"))
			updateDate = report.get("updateDate", None)
			if not updateDate:
				updateDate = report.get("creationDate", frappe.utils.now())

			ret[report.get("label")] = {"uri":report.get("uri"), "inputControls": ics, "updateDate": updateDate, "queryString": query}

		return ret

	@_jasperserver
	def get_reports_list_from_server(self, force=False):
		return self._get_reports_list_from_server(force)


	def get_jrxml_from_server(self, uri):
		f = DownloadBinary(self.session, uri)
		f.downloadBinary(file=True)
		return f.getFileContent()

	#get a jrxml file and the query associated
	def get_query_jrxmlFile_from_server(self, file_content):
		query = ""
		#file_content = self.get_jrxml_from_server(uri)
		list_query = get_query(BytesIO(file_content))
		if list_query:
			query = list_query[0].text
		print "get_reports_jrxmlFile_from_server: {} ***************************".format(query)
		return query

	def import_all_jasper_reports(self, data, force=True):
		reports = self._get_reports_list_from_server(force=force)
		docs = utils.do_doctype_from_jasper(data, reports, force=True)
		utils.import_all_jasper_remote_reports(data, docs, force)

	def _get_reports_list(self, filters_report={}, filters_param={}, force=False, cachename="report_list_all", tab="tabJasperReportListAll", update=False):
		ret = self.get_reports_list_from_db(filters_report=filters_report, filters_param=filters_param)
		#check to see if there is any report by now. If there are reports don't check the server
		if ret is None and self.use_server():
			#called from client. Don't let him change old reports attributes
			import_only_new = self.data['data'].get('import_only_new')
			self.data['data']['import_only_new'] = 1
			print "data: {}".format(self.data['data'])
			self.import_all_jasper_reports(self.data['data'], force=force)
			self.data['data']['import_only_new'] = import_only_new
			#could be recursive but there is no need for resume again because decorator
			ret = self.get_reports_list_from_db(filters_report=filters_report, filters_param=filters_param)
		ptime = self.data['data'].get('jasper_polling_time')
		if ret:
			ret['jasper_polling_time'] = ptime
		if ret and not update:
			utils.insert_list_all_memcache_db(ret, cachename=cachename, tab=tab)
		elif ret:
			utils.update_list_all_memcache_db(ret, cachename=cachename, tab=tab)
		return ret

	@_jasperserver
	def get_reports_list(self, filters_report={}, filters_param={}, force=False, cachename="report_list_all", tab="tabJasperReportListAll", update=False):
		return self._get_reports_list(filters_report=filters_report, filters_param=filters_param, force=force, cachename=cachename, tab=tab, update=update)

	def get_reports_list_from_db(self, filters_report={}, filters_param={}):
		return utils.jasper_report_names_from_db(origin=self.get_report_origin(), filters_report=filters_report, filters_param=filters_param)

	def _get_server_info(self):
		#serverInfo = "No server found"
		print "session {}".format(self.session.session.getSessionId())
		#if self.in_jasper_session():
		details = Details(self.session)
		serverInfo = details.serverInfo()
		#self.update(force_db=True)
		return serverInfo

	@_jasperserver
	def get_server_info(self):
		return self._get_server_info()
	
	@_jasperserver
	def run_remote_report(self, path, doc, data={}, params={}, pformat="pdf"):
		report = Report(self.session)
		res = report.run_remote_report(path, doc, data, params, pformat)
		return res

	def check_ids_in_hooks(self, doc, data, params):
		pram_server = [{"name": "name_ids", "attrs": params, "value": data.get('name_ids', [])}]
		res = utils.call_hook_for_param(doc, data, pram_server)
		print "res on hooks 2 {}".format(res)
		if res:
			data['name_ids'] = res[0].get('value')
		return res[0]

	@_jasperserver
	def run_remote_report_async(self, path, doc, data={}, params=[], async=True, pformat="pdf", ncopies=1):
		report = Report(self.session)
		resps = []
		#get the ids for this report from hooks. Return a list of ids
		if doc.jasper_report_type == "Server Hooks":
			self.check_ids_in_hooks(doc, data, params)

		print "Parameters is list {} name_ids {}".format(params, data.get('name_ids', []))
		if not doc.jasper_report_type == "General":
			name_ids = data.get('name_ids', [])
			if params or name_ids:
				if not name_ids:
					res = self.check_ids_in_hooks(doc, data, params)
					print "hooks res {}".format(res)
					if not res:
						#frappe.msgprint(_("There is no report."))
						frappe.throw(_("Report {} input params error. This report is of type {} and needs at least one name.".format(doc.get('name'),doc.jasper_report_type)))
						return
				#print "name_ids from hooks {}".format(data.get('name_ids'))
				if doc.jasper_report_type == "Form":
					for elem in data.get('name_ids', []):
						data['ids'] = [elem]
						resps.append(report.run_remote_report_async(path, doc, data=data, params=params, async=async, pformat=pformat, ncopies=ncopies))
				elif doc.jasper_report_type == "List":
					data['ids'] = data.get('name_ids', [])
					resps.append(report.run_remote_report_async(path, doc, data=data, params=params, async=async, pformat=pformat, ncopies=ncopies))
			else:
				resps.append(report.run_remote_report_async(path, doc, data=data, params=params, async=async, pformat=pformat, ncopies=ncopies))
		#print "reportExecution: {}".format(resp)
		else:
			resps.append(report.run_remote_report_async(path, doc, data=data, params=params, async=async, pformat=pformat, ncopies=ncopies))
		cresp = prepareCollectResponse(resps)
		#return resp[len(resp) - 1]
		cresp["origin"] = "server"
		return [cresp]

	def run_local_report_async(self, path, doc, data={}, params=[], async=True, pformat="pdf", ncopies=1, for_all_sites=1):
		resps = []
		if doc.jasper_report_type == "Server Hooks":
			self.check_ids_in_hooks(doc, data, params)
		name_ids = data.get('name_ids', [])
		if not doc.jasper_report_type == "General":
			if params or name_ids:
				if not name_ids:
					res = self.check_ids_in_hooks(doc, data, params)
					print "hooks res {}".format(res)
					if not res:
						#frappe.msgprint(_("There is no report."))
						frappe.throw(_("Report {} input params error. This report is of type {} and needs at least one name.".format(doc.get('name'),doc.jasper_report_type)))
						return
				if doc.jasper_report_type == "Form":
					for elem in data.get('name_ids', []):
						data['ids'] = [elem]
						resps.append(jasper_run_local_report(path, doc, data=data, params=params, async=async, pformat=pformat, ncopies=ncopies, for_all_sites=for_all_sites))
				elif doc.jasper_report_type == "List":
					data['ids'] = data.get('name_ids', [])
					resps.append(jasper_run_local_report(path, doc, data=data, params=params, async=async, pformat=pformat, ncopies=ncopies, for_all_sites=for_all_sites))
			else:
				resps.append(jasper_run_local_report(path, doc, data=data, params=params, async=async, pformat=pformat, ncopies=ncopies, for_all_sites=for_all_sites))
		else:
			resps.append(jasper_run_local_report(path, doc, data=data, params=params, async=async, pformat=pformat, ncopies=ncopies, for_all_sites=for_all_sites))
		cresp = prepareCollectResponse(resps)
		#return resp[len(resp) - 1]
		cresp["origin"] = "local"
		return [cresp]

	def get_local_report(self, reqId):
		return getLocalReport(reqId)

	def report_local_polling(self, reqId, reqtime):
		req = self._report_polling(reqId, getLocalPolling ,reqtime)
		return req

	def _report_polling(self, reqId, Polling, reqtime=""):
		result = []
		req = [{}]
		data = get_jasper_reqid_data(reqId)
		if data:
			d = data['data']
			print "polling {}".format(d)
			for ids in d.get('reqids'):
				for id in ids:
					res = Polling(id, reqtime)
					if res.get('status') != "ready":
						result = []
						break
					result.append(res)
				if not result:
					break
			for r in result:
				new_data = {"data":{"result": r, "last_updated": frappe.utils.now(), 'session_expiry': d.get('session_expiry')}}
				update_jasper_reqid_record(r.get('requestId'), new_data)
			if result:
				req = [{"requestId": reqId, "reqtime": frappe.utils.now(), "status": "ready"}]
		else:
			print "Report Not Found."
			frappe.throw(_("Report Not Found!!!"))
		print "result in polling local {}".format(result)
		return req

	@_jasperserver
	def report_server_polling(self, reqId):
		report = Report(self.session)
		req = self._report_polling(reqId, report.pollingReport)
		return req

	@_jasperserver
	def report_server_polling2(self, reqId):
		result = []
		report = Report(self.session)
		data = get_jasper_reqid_data(reqId)
		if data:
			d = data['data']
			for ids in d.get('reqids'):
				for id in ids:
					res = report.pollingReport(id)
					if res.status != "ready":
						result = [{}]
						break
					result.append(res)
				if not result[0]:
					break
			if result[0]:
				new_data = {"data":{"result": result, "last_updated": frappe.utils.now(), 'session_expiry': d.get('session_expiry')}}
				update_jasper_reqid_record(id, new_data)
				result = [{"requestId": reqId, "reqtime": frappe.utils.now(), "status": "ready"}]
		else:
			print "Report Not Found."
			frappe.throw(_("Report Not Found!!!"))

		return result

	@_jasperserver
	def get_report(self, reqId, expId):
		report = Report(self.session)
		return report.getReport(reqId, expId)
#def make_jasper_report_list_session(data):
#	frappe.cache().set_value("jasper:jaspersession_report_list", data)
def import_all_jasper_reports(data, force=True):
	docs = make_doctype_from_jasper(data, force=force)
	utils.import_all_jasper_remote_reports(data, docs, force)

def make_doctype_from_jasper(data, force=True):
	reports = __get_reports_list(force=force)
	return utils.do_doctype_from_jasper(data, reports, force=True)

#called after successfully login...
def on_session_creation(login_manager):
	_logger.info("jasperserver on creation session {0} GUEST? {1}".format(login_manager, frappe.session['user'] == 'Guest'))
	if frappe.session['user'] != 'Guest':
		JasperServerSession()._login()
	else:
		#maybe session timeout!
		jasper_logout()

def on_logout(login_manager):
	#_logger.info("jasperserver on_logout ")
	jasper_logout()

def boot_session(bootinfo):
	#_logger.info("jasperserver boot_session {}".format(bootinfo))
	#pass
	#bootinfo['jasper_server_info'] = get_server_info()
	bootinfo['jasper_reports_list'] = get_reports_list_for_all()
	
	#return bootinfo
	
#def website_clear_cache():
#	_logger.info("jasperserver website_clear_cache")
	#_logger.info("jasperserver clear_cache called {}".format(frappe.get_traceback()))

	#frappe.db.sql("""delete from tabJasperSessions where sid=%s""", sid)
	#clear_cache()
	#for sid in frappe.db.sql_list("""select sid
	#	from tabJasperSessions where TIMEDIFF(NOW(), lastupdate) > TIME(%s)""", get_expiry_period()):
	#	delete_jasper_session(sid)

#TODOS
#check permission on doctype
@frappe.whitelist()
def get_doctype_reports_list(doc):
	utils.validate_print_permission(doc)
	js = jasper_session_obj or JasperServerSession()
	r_filters={"jasper_doctype":doc.doctype}
	#ret = jasper_report_names_from_db(origin=js.get_report_origin(), filters=r_filters)
	#if ret is None and js.use_server():
	ret = js.get_reports_list(filters=r_filters)
	return ret

def get_jasper_report_list_from_db(tab="tabJasperReportListAll"):
	#print "get_jasper_report_list_from_db tab {}".format(tab)
	rec = frappe.db.sql("""select name, data
		from {0} where
		TIMEDIFF(NOW(), lastupdate) < TIME("{1}")""".format(tab, utils.get_expiry_period("report_list_all")))
	return rec

@frappe.whitelist()
def get_reports_list_for_all():
	#print "data dirt2 {}".format(data)
	if frappe.local.session['sid'] == 'Guest':
		return None
	data = {}
	dirt = utils.jaspersession_get_value("report_list_dirt_all")
	print "dirty!! {}".format(dirt)
	#dirt = False
	if not dirt:
		#data = get_jasper_data("report_list_all", get_from_db=lambda: get_jasper_report_list_from_db)
		data = utils.get_jasper_data("report_list_all", get_from_db=get_jasper_report_list_from_db)

	if not data:
		utils.delete_jasper_session("report_list_all", "tabJasperReportListAll")
		js = jasper_session_obj or JasperServerSession()
		#r_filters={"jasper_doctype": None, "report": None}
		#just get reports with NULL fields. For each key any value will do except 0
		#r_filters={"jasper_doctype": ["is","NULL"], "report": ["is", "NULL"]}
		r_filters=["`tabJasper Reports`.jasper_doctype is NULL", "`tabJasper Reports`.report is NULL"]
		data = js.get_reports_list(filters_report=r_filters)
		print "data new {}".format(data)
	if data:
		utils.jaspersession_set_value("report_list_dirt_all", False)
		data.pop('session_expiry',None)
		data.pop('last_updated', None)
		#print "data dirt3 {}".format(data)
		if frappe.local.session['user'] != "Administrator":
			filter_perm_roles(data)

	return data

def filter_perm_roles(data):
	#user_roles = frappe.get_roles(frappe.local.session['user'])
	#print "get_roles: {}".format(user_roles)
	removed = 0
	toremove = []
	for k,v in data.iteritems():
		#print "v type {}".format(type(v))
		if isinstance(v, dict):
			#found = False
			perms = v.pop("perms", None)
			print "perms {}".format(perms)
			found = utils.check_jasper_perm(perms)
			if not found:
				toremove.append(k)
				removed = removed + 1
	for k in toremove:
		data.pop(k, None)
	data['size'] = data['size'] - removed

@frappe.whitelist()
def get_reports_list(doctype, docnames):
	#return get_doctype_reports_list("None")
	#_logger.info("jasperserver get_reports_list ")
	#if not doctype or not docnames:
	if not doctype:
		frappe.throw(_("You need to provide the doctype name!!!"))
	if docnames:
		docnames = json.loads(docnames)
	else:
		docnames = []

	new_data = {}
	added = 0
	#def myfunc():
	#	return get_jasper_report_list_from_db(tab="tabJasperReportListDoctype")
	if frappe.local.session['sid'] == 'Guest':
		return None

	dirt = utils.jaspersession_get_value("report_list_dirt_doc")
	data = {}
	#dirt = False
	if not dirt:
		#data = get_jasper_data("report_list_doctype", get_from_db=lambda: myfunc)
		data = utils.get_jasper_data("report_list_doctype", get_from_db=get_jasper_report_list_from_db, tab="tabJasperReportListDoctype")

	if not data or not check_docname(data, doctype):
		utils.delete_jasper_session("report_list_doctype", "tabJasperReportListDoctype")
		js = jasper_session_obj or JasperServerSession()
		r_filters={"jasper_doctype": doctype}
		update = False if not data else True
		data = js.get_reports_list(filters_report=r_filters, cachename="report_list_doctype", tab="tabJasperReportListDoctype", update=update)

	#print "list doc {}".format(docnames)
	if data and check_docname(data, doctype):
		utils.jaspersession_set_value("report_list_dirt_doc", False)
		data.pop('session_expiry',None)
		data.pop('last_updated', None)
		for k,v in data.iteritems():
			if isinstance(v, dict):
				if v.get("Doctype name") == doctype:
					#if not docnames then we are in List, then we be sure that only List report go!
					#if not docnames and not v.get('jasper_report_type') == "List":
					#	continue
					if docnames and v.get('jasper_report_type') == "List":
						continue
					if frappe.local.session['user'] != "Administrator":
						#filter_perm_roles(data)
						#if docnames:
						for docname in docnames:
							for ptype in ("read", "print"):
								if not frappe.has_permission(doctype, ptype=ptype, doc=docname, user=frappe.local.session['user']):
									#raise frappe.PermissionError(_("No {0} permission").format(ptype))
									print "No {0} permission for doc {1}".format(ptype, docname)
									continue
						rdoc = frappe.get_doc("Jasper Reports", k)
						print "rdoc for list reports {}".format(rdoc.jasper_roles)
						if not utils.check_jasper_doc_perm(rdoc.jasper_roles):
							#raise frappe.PermissionError(_("No read permission"))
							print "No {0} permission!".format("read")
							continue
					#else:
					new_data[k] = v
					added = added + 1
	#js = jasper_session_obj or JasperServerSession()
	#data = js.get_reports_list(filters_report=r_filters)
	#ret = js.get_reports_list(force=True)
	new_data['size'] = added

	return new_data

#check if exist at least one docname in data
def check_docname(data, doctype):
	ret = False
	if not data:
		return ret
	for k,v in data.iteritems():
		if isinstance(v, dict):
			if v.get("Doctype name") == doctype:
				ret = True
				break
	return ret

"""@frappe.whitelist()
def get_reports_list():
	#_logger.info("jasperserver get_reports_list ")
	js = JasperServerSession()
	ret = jasper_report_names_from_db(origin=js.get_report_origin())
	if ret is None and js.use_server():
		#_logger.info("jasperserver get_reports_list ret {}".format(ret))
		ret = __get_reports_list(js, force=True)

	return ret or {}"""

def __get_reports_list(force=False):
	ret = {}
	#js = JasperServerSession() if js is None else js
	js = jasper_session_obj or JasperServerSession()
	if js.use_server():
		ret = js.get_reports_list_from_server(force)

	return ret

@frappe.whitelist()
def get_server_info():
	#_logger.info("jasperserver get_server_info ")
	#with JasperServerSession() as js:
	#return
	js = jasper_session_obj or JasperServerSession()	#if js:
	if js.use_server():
		info = js.get_server_info()
	else:
		info = "Local jrxml only"

	return info

@frappe.whitelist()
def jasper_logout():
	#_logger.info("jasperserver jasper_logout whitelist ")
	#with JasperServerSession() as js:
		#if js:
	js = jasper_session_obj or JasperServerSession()
	return js._logout()

@frappe.whitelist()
def report_polling(data):
	if not data:
		frappe.throw(_("No data for to be polling!!!"))
	data = json.loads(data)
	validate_ticket(data)
	js = jasper_session_obj or JasperServerSession()
	try:
		reqIds = data.get("reqIds")
		reqtime = data.get("reqtime")
		pformat = data.get("pformat")
		#if reqIds[0].startswith("local_report_"):
		#if reqIds[0].startswith("intern_reqid_"):
		if data.get("origin") == "local":
			#reqId = reqIds[6:]
			print "is local report {}".format(reqIds)
			result = js.report_local_polling(reqIds[0], reqtime)
		else:
			#check only one requestId
			result = js.report_server_polling(reqIds[0])
		print "result from polling {}".format(result)
		result[0]["pformat"] = pformat
	except NotFound:
		frappe.throw(_("Not Found!!!"))
	return result

@frappe.whitelist()
def get_report(data):
	try:
		print "data get_reportssss {}".format(unquote(data))
		if not data:
			frappe.throw(_("No data for this Report!!!"))
		data = json.loads(unquote(data))
		_get_report_server(data)
	except NotFound:
		frappe.throw(_("Not Found!!!"))

@frappe.whitelist()
def run_report(data, docdata=None, rtype="Form"):
	if not data:
		frappe.throw("No data for this Report!!!")
	#data = json.loads(unquote(data))
	data = json.loads(data)
	#print "data run_report {0} string {1}".format(data, isinstance(data, basestring))
	doctype = data.get('doctype')
	rdoc = frappe.get_doc(doctype, data.get('report_name'))
	#fortype maybe of type "doctype" or type "report"
	if data.get("fortype").lower() == "doctype" and rtype in ("List", "Form"):
		#doc.in_print = True
		#validate_print_permission(doc)
		for docname in data.get('name_ids'):
			for ptype in ("read", "print"):
				if not frappe.has_permission(rdoc.jasper_doctype, ptype=ptype, doc=docname, user=frappe.local.session['user']):
					#doc.in_print = False
					raise frappe.PermissionError(_("No {0} permission for doc {1} in doctype {3}!").format(ptype, docname, rdoc.jasper_doctype))
		#if user can read doc it is possible that can't print it! Just uncheck Read permission in doctype Jasper Reports
		if not utils.check_jasper_doc_perm(rdoc.jasper_roles):
			#doc.in_print = False
			raise frappe.PermissionError(_("No print permission!"))
	else:
		if not utils.check_jasper_perm(rdoc.jasper_roles):
			raise frappe.PermissionError(_("No print permission!"))
	params = rdoc.jasper_parameters
	origin = rdoc.jasper_report_origin.lower()
	result = []
	pformat = data.get('pformat')
	copies = [_("Single"), _("Duplicated"), _("Triplicate")]
	try:
		ncopies = copies.index(rdoc.jasper_report_number_copies) + 1 if pformat == "pdf" else 1
		js = jasper_session_obj or JasperServerSession()
		if origin == "localserver":
			path = rdoc.jasper_upload_jrxml
			if not path:
				frappe.throw(_("%s: Import first a jrxml file!!!" % rdoc.name))
			for_all_sites = rdoc.jasper_all_sites_report
			result = js.run_local_report_async(path, rdoc, data=data, params=params, async=True, pformat=pformat, ncopies=ncopies, for_all_sites=for_all_sites)
		else:
			path = rdoc.jasper_report_path
			#print "is for server call path {0} rdoc {1}".format(path, rdoc)
			result = js.run_remote_report_async(path, rdoc, data=data, params=params, async=True, pformat=pformat, ncopies=ncopies)
		result[0]["pformat"] = pformat
	except ValueError:
		frappe.throw(_("Report number of copies error %s!!!" % rdoc.name))
	#finally:
	#	if doc:
	#		doc.in_print = False

	return result

"""@frappe.whitelist()
def run_report(data, doc=None, type="reports"):
	if not data:
		frappe.throw("No data for this Report!!!")
	data = json.loads(unquote(data))
	#print "data run_report {0} string {1}".format(data, isinstance(data, basestring))
	if doc:
		doc.in_print = True
	doctype = data.get('doctype')
	rdoc = frappe.get_doc(doctype, data.get('report_name'))
	#validate_print_permission(doc)
	for ptype in ("read", "print"):
		if not frappe.has_permission(rdoc.jasper_doctype, ptype, doc):
			raise frappe.PermissionError(_("No {0} permission").format(ptype))
	params = rdoc.jasper_parameters
	origin = rdoc.jasper_report_origin.lower()
	if origin == "localserver":
		pass
	else:
		path = rdoc.jasper_report_path
		pformat = data.get('pformat')
		if type == "reports":
			ret = _run_report_server(path, data=data, params=params, pformat=pformat)
		else:
			ret = _run_report_server_doc(path, data=data, params=params, pformat=pformat)
		return ret
"""

def _get_report_server(data):
	#_logger.info("jasperserver run_report whitelist {}".format(unquote(data)))
	#with JasperServerSession() as js:
		#if js:
	#check if this requestId is older than last timeout
	validate_ticket(data)
	d = get_jasper_reqid_data(data.get('requestId'))
	if not d:
		frappe.throw(_("Report Not Found!!!"))
	reqids = d['data'].get('reqids')
	print "new reqids {}".format(d)
	content = []
	fileName = None
	try:
		for ids in reqids:
			for id in ids:
				report = get_jasper_reqid_data(id)
				print "new report {}".format(report)
				rdata = report['data'].get('result')
				reqId = [rdata.get("requestId")]
				expId = rdata.get("ids")
				pformat = data.get("pformat")
				print "expID array {}".format(expId)
				fileName = expId[0].get("fileName", None)
				js = jasper_session_obj or JasperServerSession()
				rid_len = 1
				print "before get report local {}".format(reqId)
				#if js.use_server():
				if not any("local_report" in r for r in reqId):
					eid_len = len(expId)
					#if lens not equal then process only the first
					if rid_len == eid_len:
						for i in range(rid_len):
							content.append(js.get_report(reqId[i], expId[i].get('id')))
					else:
						content.append(js.get_report(reqId[0], expId[0].get('id')))
				else:
					for i in range(rid_len):
						print "get report local {}".format(reqId[i])
						content.append(js.get_local_report(reqId[i]))
	except:
		return frappe.msgprint(_("There is no report."))

	if fileName:
		fileName = fileName[fileName.rfind(os.sep) + 1:]
		output = StringIO.StringIO()
		file_name = fileName.replace(" ", "-").replace("/", "-")
		if pformat=="pdf":
			merger = PdfFileMerger()
			for n in range(len(content)):
				merger.append(BytesIO(content[n]))
			merger.write(output)
			#relat_conent = output.getvalue()
			#print "********************* problems not here *******************"
		else:
			fname = file_name.split(".")
			myzip = zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED)
			#zipname = fname[0] + ".zip"
			try:
				for n in range(len(content)):
					#with zipfile.ZipFile(output, 'w') as myzip:
					myzip.writestr(fname[0] + "_" + str(n) + "." + fname[1], content[n])
			finally:
				myzip.close()
			#print "name of zip {} n {}".format(zipname, n)
			#frappe.local.response.filename = "{name}".format(name=zipname)
			file_name = fname[0] + ".zip"
			#relat_conent = content[0]
		#relat_conent = output.getvalue()
		frappe.local.response.filename = "{name}".format(name=file_name)
		frappe.local.response.filecontent = output.getvalue()
		frappe.local.response.type = "download"
	else:
		#frappe.throw(_("Report must have a path!!!"))
		frappe.msgprint(_("There is no report."))

"""
def _get_report_server(data):
	#_logger.info("jasperserver run_report whitelist {}".format(unquote(data)))
	#with JasperServerSession() as js:
		#if js:
	#check if this requestId is older than last timeout
	validate_ticket(data)
	reqId = data.get("reqId")
	expId = data.get("expId")
	pformat = data.get("pformat")
	print "expID array {}".format(expId)
	fileName = data.get("fileName")
	js = jasper_session_obj or JasperServerSession()
	#data = unquote(data)
	content = []
	rid_len = len(reqId)
	print "before get report local {}".format(reqId)
	#if js.use_server():
	if not any("local_report" in r for r in reqId):
		eid_len = len(expId)
		#if lens not equal then process only the first
		if rid_len == eid_len:
			for i in range(rid_len):
				content.append(js.get_report(reqId[i], expId[i]))
		else:
			content.append(js.get_report(reqId[0], expId[0]))
	else:
		for i in range(rid_len):
			print "get report local {}".format(reqId[i])
			content.append(js.get_local_report(reqId[i]))

	if fileName:
		fileName = fileName[fileName.rfind(os.sep) + 1:]
		if pformat=="pdf":
			merger = PdfFileMerger()
			for n in range(len(content)):
				merger.append(BytesIO(content[n]))
			output = StringIO.StringIO()
			merger.write(output)
			relat_conent = output.getvalue()
		else:
			relat_conent = content[0]
		frappe.local.response.filename = "{name}".format(name=fileName.replace(" ", "-").replace("/", "-"))
		frappe.local.response.filecontent = relat_conent
		frappe.local.response.type = "download"
	else:
		frappe.throw(_("Report must have a path!!!"))
"""

def validate_ticket(data):
	last_timeout = utils.jaspersession_get_value("last_jasper_session_timeout")
	request_time = data.get("reqtime")
	time_diff = frappe.utils.time_diff_in_seconds(request_time, last_timeout) if last_timeout else None
	if time_diff and time_diff < 0:
		frappe.throw("RequestID not Valid!!!")

#called from query-reports
#@frappe.whitelist()
"""def _run_report_server(path, data={}, params={}, pformat="pdf"):
	#_logger.info("jasperserver run_report whitelist {}".format(unquote(data)))
	#with JasperServerSession() as js:
		#if js:
	js = jasper_session_obj or JasperServerSession()
	path = unquote(path)
	#data = unquote(data)
	if js.use_server():
		content = js.run_remote_report_async(path, data, params=params, async=True, pformat=pformat)
	else:
		content = ""

	k = path.rfind(os.sep)
	if k != -1:
		name = path[k+1:]
		frappe.local.response.filename = ("{name}.%s" % (pformat,)).format(name=name.replace(" ", "-").replace("/", "-"))
		frappe.local.response.filecontent = content
		frappe.local.response.type = "download"
	else:
		frappe.throw("Report must have a path!!!")
"""
#called from doctype documents
#@frappe.whitelist()
def _run_report_server_doc(path, doc={}, params={}, pformat="pdf"):
	return
	#doc.in_print = True
	#validate_print_permission(doc)
	js = jasper_session_obj or JasperServerSession()
	path = unquote(path)
	if js.use_server():
		content = js.run_remote_report_async(path, doc, params=params, async=True, pformat=pformat)
	else:
		content = ""

	k = path.rfind(os.sep)
	if k != -1:
		name = path[k+1:]
		frappe.local.response.filename = ("{name}.%s" % (pformat,)).format(name=name.replace(" ", "-").replace("/", "-"))
		frappe.local.response.filecontent = content
		frappe.local.response.type = "download"
	else:
		frappe.throw(_("Report must have a path!!"))
				
	#doc.in_print = False



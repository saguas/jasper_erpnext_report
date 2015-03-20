from __future__ import unicode_literals
__author__ = 'luissaguas'

from jasper_erpnext_report import jasperserverlib

try:
	import jasperserver.core as jasper
	from jasperserver.core.reportingService import ReportingService
	from jasperserver.core.ReportExecutionRequest import ReportExecutionRequest
	from jasperserver.resource_details import Details
	from jasperserver.repo_search import Search
	from jasperserver.resource_download import DownloadBinary
	from jasperserver.core.exceptions import Unauthorized, NotFound
	jasperserverlib = True
except:
	jasperserverlib = False
	pass

from frappe.utils import pprint_dict


from jasper_erpnext_report.utils.report import prepareCollectResponse

from frappe import _
import frappe

import logging, json
from io import BytesIO
import inspect

from jasper_erpnext_report.utils.file import JasperXmlReport
import jasper_erpnext_report.utils.utils as utils

import JasperBase as Jb

from frappe.core.doctype.communication.communication import make

_logger = logging.getLogger(frappe.__name__)



def _jasperserver(fn):
	"""
	decorator for jasperserver functions
	"""
	def innerfn(*args, **kwargs):
		newargs = {}
		me = args[0]
		try:
			fnargs, varargs, varkw, defaults = inspect.getargspec(fn)
			for a in fnargs:
				if a in kwargs:
					newargs[a] = kwargs.get(a)
			fn_result = fn(*args, **newargs)
			me.update()
			return fn_result

		except Unauthorized as e:
			_logger.info("************************Decorator _jasperserver error {2} args {0} newargs {1}".format(args, newargs, e))
			me._timeout()
			fn_result = fn(*args, **newargs)
			me.update()
			utils.jaspersession_set_value("last_jasper_session_timeout", frappe.utils.now())
			return fn_result
		except Exception as e:
			print "problems!!!! {}\n".format(e)

	return innerfn



class JasperServer(Jb.JasperBase):
	def __init__(self, doc={}):
		self.is_login = False
		self.session = frappe.local.jasper_session = frappe._dict({'session': frappe._dict({})})
		super(JasperServer, self).__init__(doc)
		self.check_session()

	def check_session(self):
		if not jasperserverlib:
			return
		if self.data['data'] and self.data['data'].get('cookie', None):
			self.resume_connection()
		else:
			self.login()

	def login(self):
		self.connect()
		if not self.in_jasper_session() and self.user == "Administrator":
			#frappe.throw(_("Jasper Server is down. Please check jasperserver or change to local report only (you will need pyjnius)."))
			self.send_email(_("Jasper Server is down. Please check jasperserver or change to local report only (you will need pyjnius)."), _("jasperserver login error"))

	def in_jasper_session(self):
		try:
			session = bool(self.session.session.getSessionId())
		except:
			session = False

		return session

	def resume_connection(self):
		self.session = frappe.local.jasper_session = jasper.session(self.doc.get("jasper_server_url"), resume=True)
		if self.session:
			self.session.resume(self.data['data']['cookie'])
			self.is_login = True


	def connect(self):
		if self.user=="Guest":
			return

		try:
			if not self.doc:
				#self.doc = frappe.db.get_value('JasperServerConfig', None, "*", ignore=True, as_dict=True)
				#self.createJasperSession()
				self.get_jasperconfig_from_db()

			print "BEFORE jasper session connect doc 1 {}".format(self.doc)
			self.session = frappe.local.jasper_session = jasper.session(self.doc.get("jasper_server_url"), self.doc.get("jasper_username"), self.doc.get("jasper_server_password"))
			print "AFTER jasper session connect {}".format(self.session)
			self.update_cookie()
			self.is_login = True

		except Exception as e:
			self.is_login = False
			#if self.user == "Administrator":
			_logger.info("jasperserver login error")
				#frappe.msgprint(_("JasperServer login error, reason: {}".format(e)))
			#else:
			cur_user = "no_reply@gmail.com" if self.user == "Administrator" else self.user
			self.send_email(_("JasperServer login error, reason: {}".format(e)), _("jasperserver login error"), user=cur_user)

	def logout(self):
		if self.session:
			self.session.logout()

	def _timeout(self):
		try:
			self.logout()
			self.login()
		except:
			_logger.info("_login: JasperServerSession Error while timeout and login")

		_logger.info("_timeout JasperServerSession login successfuly {0}".format(self.doc))

	def update_cookie(self):
		print "frappe.local.jasper_session.session.getSessionId() {}".format(frappe.local.jasper_session.session.getSessionId())
		self.data['data']['cookie'] = frappe.local.jasper_session.session.getSessionId() if frappe.local.jasper_session.session else {}
		self.update(force_cache=False, force_db=True)

	def get_server_info(self):
		print "session {}".format(self.session.session.getSessionId())
		details = Details(self.session)
		serverInfo = details.serverInfo()
		return serverInfo

	def get_jrxml_from_server(self, uri):
		f = DownloadBinary(self.session, uri)
		f.downloadBinary(file=True)
		return f.getFileContent()

	def import_all_jasper_reports(self, data, force=True):
		if self.is_login:
			reports = self.get_reports_list_from_server(force=force)
			docs = utils.do_doctype_from_jasper(data, reports, force=True)
			utils.import_all_jasper_remote_reports(docs, force)

	@_jasperserver
	def get_reports_list_from_server(self, force=False):
		ret = {}
		s = Search(self.session)
		result = s.search(path=self.doc.get("jasper_report_root_path"), type="reportUnit")
		reports = result.getDescriptor().json_descriptor()
		for report in reports:
			ics = []
			d = Details(self.session, report.get("uri"))
			r_details = d.details(expanded=False)
			r_param = r_details.getDescriptor().json_descriptor()
			uri = r_param[0].get('jrxml').get('jrxmlFileReference').get('uri')
			file_content = self.get_jrxml_from_server(uri)
			xmldoc = JasperXmlReport(BytesIO(file_content))
			params = xmldoc.get_params()
			query = self.get_query_jrxmlFile_from_server(file_content)
			for param in params:
				pname = param.xpath('./@name')
				pclass = param.xpath('./@class')
				ptype = pclass[0].split(".")
				c = len(ptype) - 1
				ics.append({"label":pname[0], "type":ptype[c].lower()})
			updateDate = report.get("updateDate", None)
			if not updateDate:
				updateDate = report.get("creationDate", frappe.utils.now())

			ret[report.get("label")] = {"uri":report.get("uri"), "inputControls": ics, "updateDate": updateDate, "queryString": query}

		return ret

	def run_remote_report_async(self, path, doc, data={}, params=[], pformat="pdf", ncopies=1):
		resps = []
		#data = self.run_report_async(path, doc, data=data, params=params, async=async, pformat=pformat, ncopies=ncopies)
		data = self.run_report_async(doc, data=data, params=params)
		"""
		Run one report at a time for Form type report and many ids
		"""
		if data.get('jasper_report_type', None) == "Form" or doc.jasper_report_type == "Form":
			ids = data.get('ids')
			for id in ids:
				data['ids'] = [id]
				resps.append(self._run_report_async(path, doc, data=data, params=params, pformat=pformat, ncopies=ncopies))
		else:
			resps.append(self._run_report_async(path, doc, data=data, params=params, pformat=pformat, ncopies=ncopies))
		cresp = self.prepareCollectResponse(resps)
		cresp["origin"] = "server"
		return [cresp]

	#run reports with http POST and run async and sync
	def _run_report_async(self, path, doc, data={}, params=[], pformat="pdf", ncopies=1):
		pram, pram_server, copies = self.do_params(data, params, pformat)
		pram_copy_index = copies.get("pram_copy_index", -1)
		pram_copy_page_index = copies.get("pram_copy_page_index", -1)
		"""
		pram = []
		#self.doc = doc
		#pram.extend(self.get_ask_params(data))
		pram_server = []
		pram_copy_index = -1
		pram_copy_page_index = -1
		for param in params:
			is_copy = param.is_copy.lower()
			p = param.jasper_param_name
			value = ""
			if is_copy == _("is for where clause"):
				#value = data.get('name_ids')
				value = self.get_where_clause_value(data.get('ids'), param)
				#print "value in where clause value {} name".format(value, param.name)
				#value = "where name %s (%s)" % (param.param_expression, ",".join(a))
			elif is_copy == _("is for copies") and pformat=="pdf":
				#set the number of copies
				#indicate the index of param is for copies
				pram_copy_index = len(pram) - 1 if len(pram) > 0 else 0
			elif is_copy == _("is for page number") and pformat=="pdf":
				pram_copy_page_index = len(pram) - 1 if len(pram) > 0 else 0
			elif is_copy == _("is for server hook"):
				value = data.get('ids')
				if not value:
					#if not data and not entered value then get default
					value = utils.get_value_param_for_hook(param)
				pram_server.append({"name":p, 'value': value, "attrs": param})
				continue
			else:
				#value sent take precedence from value in doctype jasper_param_value
				value = data.get("params", {}).get(p) or param.jasper_param_value
				#value = data.get(p) or param.jasper_param_value
			pram.append({"name":p, 'value':[value]})
		"""
		resp = []
		"""
		Hook must return a list of dict with fields: {"name":"name of param", "value": [value_of_param], "param_type": "_(is for where clause)"}
		param_type is optional
		"""
		"""
		res = utils.call_hook_for_param(doc, "on_jasper_params", data, pram_server) if pram_server else []
		for param in res:
			param.pop("attrs", None)
			#del param["attrs"]
			param_type = param.pop("param_type", None)
			print "pvalue {}".format(res)
			if param_type and param_type.lower() == _("is for where clause"):
				param.setdefault("param_expression", "In")
				#print "param_expression 2 {}".format(param.param_expression)
				value = self.get_where_clause_value(param.get("value", None), frappe._dict(param))
				#pram.append({"name":param.get("name", None), 'value':[value]})
				param["value"] = [value]
				param.pop("param_expression", None)
				#print "value from hook where 3 value {} name {}".format(param.get("value"), param.get("name"))
				#continue
			pram.append(param)
		"""
		pram.extend(self.get_param_hook(doc, data, pram_server))

		copies = [_("Single"), _("Duplicated"), _("Triplicate")]

		for m in range(ncopies):
			if pram_copy_index >= 0:
				pram[pram_copy_index]['value'] = [copies[m]]
			if pram_copy_page_index >= 0:
				pram[pram_copy_page_index]['value'] = [str(m) + _(" of ") + str(ncopies)]
			result = self.run_async(path, pram, data.get("report_name"), pformat=pformat)
			if result:
				requestId = result.get('requestId')
				reqDbObj = {"data":{"result": result, "report_name": data.get("report_name"), "last_updated": frappe.utils.now(),'session_expiry': utils.get_expiry_period()}}
				self.insert_jasper_reqid_record(requestId, reqDbObj)
				resp.append({"requestId":requestId, "report_name": data.get("report_name"), "status": result.get('status')})
			else:
				frappe.msgprint(_("There was an error in report request "),raise_exception=True)
		#TODO get reqId for check report state
		return resp

	@_jasperserver
	def run_async(self, path, pram, report_name, pformat="pdf"):
		rs = ReportingService(self.session)
		rr = ReportExecutionRequest()
		rr.setReportUnitUri(path)
		rr.setOutputFormat(pformat)
		rr.setParameters(pram)
		rr.setAsync(True)
		if pformat == "html":
			#from jasper_erpnext_report.utils.file import get_html_reports_images_path
			#import os, jasper_erpnext_report
			#host_url = frappe.local.request.host_url
			#rr.setBaseUrl(host_url)
			#path_jasper_module = os.path.dirname(jasper_erpnext_report.__file__)
			#full_path = get_html_reports_images_path(report_name, "reports")
			#relat_path = os.path.relpath(full_path, os.path.join(path_jasper_module, "public"))
			#print "report_name in run async 3 {}".format(host_url + "assets/jasper_erpnext_report/" + relat_path + "/")
			#rr.setAttachmentsPrefix("http://localhost:8000/assets/css/images/Employees/")
			#rr.setAttachmentsPrefix(host_url + "assets/jasper_erpnext_report/" + relat_path + "/")
			rr.setAttachmentsPrefix("./images/")
		try:
			req = rs.newReportExecutionRequest(rr)
			res = req.run().getResult("content")
			print "res from server 2: {}".format(res)
			res = json.loads(res)
			resp = self.prepareResponse(res, res.get("requestId"))
			resp["status"] = res.get("status")
			return resp
		except Exception as e:
			if isinstance(e, Unauthorized):
				print "e inside is : {}".format(e)
				raise Unauthorized
			else:
				frappe.throw(_("Error in report %s, server error is: %s!!!" % (self.doc.jasper_report_name, e)))

	@_jasperserver
	def polling(self, reqId):
		print "making the write polling!"
		res = []
		try:
			rs = ReportingService(self.session)
			rexecreq = rs.reportExecutionRequest(reqId)
			status = rexecreq.status().content
			print "status: status {} rexecreq {}".format(status, rexecreq)
			status = json.loads(status)
			if status.get("value") == "ready":
				detail = self.reportExecDetail(rexecreq)
				print "report detail 2: {} reqId {}".format(detail, reqId)
				res = self.prepareResponse(detail, reqId)
				if res.get('status', "") == "not ready":
					res = self.prepareResponse({}, reqId)
				else:
					res["status"] = "ready"
			elif status.get("value") == "failed":
				frappe.throw(_("Error in report %s, server error is: %s!!!" % (self.doc.jasper_report_name, status['errorDescriptor'].get('message'))))
			else:
				res = self.prepareResponse({}, reqId)
		except NotFound:
			frappe.throw(_("Not Found!!!"))
		return res

	#rexecreq : ReportExecutionRequestBuilder instance
	#check if the report is ready and get the expids for ready reports
	def reportExecDetail(self, rexecreq):
		return rexecreq.executionDetails()

	#rs: ReportingService instance
	#get the report with reqId for the given expId
	@_jasperserver
	def getReport(self, reqId, expId):
		try:
			rs = ReportingService(self.session)
			rexecreq = rs.reportExecutionRequest(reqId, expId)
			report = rexecreq.export().outputResource().getResult("content")
			return report
		except NotFound:
			frappe.throw(_("Not Found!!!"))

	def getAttachment(self, reqId, expId, attachmentId):
		print "getting attach {}".format(attachmentId)
		try:
			rs = ReportingService(self.session)
			rexecreq = rs.reportExecutionRequest(reqId, expId)
			content = rexecreq.export().attachment(attachmentId)
			#print "attachment content 5 {}".format(content)
			return content
		except NotFound:
			frappe.throw(_("Not Found!!!"))

	def send_email(self, body, subject, user="no_reply@gmail.com"):
		import frappe.utils.email_lib
		#admin_mail = frappe.db.get_value("User", "Administrator", "email")
		#print "admin_mails {}".format(frappe.utils.email_lib.get_system_managers())
		#make(doctype="JasperServerConfig", content=body, subject=subject, sender=user, recipients=[admin_mail], send_email=True)
		try:
			frappe.utils.email_lib.sendmail_to_system_managers(subject, body)
		except Exception as e:
			_logger.info(_("jasperserver email error: {}".format(e)))
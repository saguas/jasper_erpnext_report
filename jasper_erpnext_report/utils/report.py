__author__ = 'luissaguas'

#from jasperserver.report import Report as jsReport
from jasperserver.core.reportingService import ReportingService
from jasperserver.core.ReportExecutionRequest import ReportExecutionRequest
import json
import frappe
from frappe import _
import uuid
#import re
#import urllib2

from jasper_erpnext_report.utils.utils import call_hook_for_param, get_value_param_for_hook, jaspersession_set_value, get_expiry_period,\
						get_jasper_data, delete_jasper_session

class Report():
	def __init__(self, session):
		self.session = session

	#run reports with http GET
	def run_remote_report(self, path, data={}, params={}, pformat="pdf"):
		#_logger.info("jasperserver in run after clear jasper sessions {}".format(path))
		res = ""
		#if self.in_jasper_session():
		return self.run_remote_report_async(path, data, params, pformat)
		r = Report(self.session, path)
		for param in params:
			is_copy = param.is_copy.lower()
			if is_copy == "is for where clause":
				a = ["'%s'" % t for t in data.get('name_ids')]
				value = "where name %s (%s)" % (param.param_expression, ",".join(a))
				p = param.jasper_param_name
			elif is_copy == "is for copies":
				pass
			else:
				p = param.jasper_param_name
				#value sent take precedence from value in doctype jasper_param_value
				value = data.get(p) or param.jasper_param_value
			r.parameter(p,value)
		#r.updateInputControls()
		#print "inputcontrols structure {}".format(r.inputControls())
		res = r.run(reportFormat=pformat, use_params=True).getReportContent()
		#self.update(force_db=True)
		return res

	#run reports with http POST and run async and sync
	def run_remote_report_async(self, path, doc, data={}, params=[], async=True, pformat="pdf", ncopies=1):
		#rs = ReportingService(self.session)
		#rr = ReportExecutionRequest()
		#TODO make request
		pram = []
		self.doc = doc
		#rr.setReportUnitUri(path)
		#rr.setOutputFormat(pformat)
		pram_server = []
		pram_copy_index = -1
		pram_copy_page_index = -1
		for param in params:
			is_copy = param.is_copy.lower()
			p = param.jasper_param_name
			value = ""
			if is_copy == _("is for where clause"):
				#value = data.get('name_ids')
				value = data.get('ids')
				if value:
					a = ["'%s'" % t for t in value]
				else:
					value = get_value_param_for_hook(param)
					if not isinstance(value, basestring):
						a = ["'%s'" % t for t in list(value)]
					else:
						a = list(a)
				value = "where name %s (%s)" % (param.param_expression, ",".join(a))
			elif is_copy == _("Is for copies") and pformat=="pdf":
				#set the number of copies
				#indicate the index of param is for copies
				pram_copy_index = len(pram) - 1 if len(pram) > 0 else 0
			elif is_copy == _("is for page number") and pformat=="pdf":
				pram_copy_page_index = len(pram) - 1 if len(pram) > 0 else 0
			elif is_copy == _("is for server hook"):
				#value = call_hook_for_param(doc, data, param)
				#if we get value from input or from data then ignore default
				#value = data.get('name_ids')
				value = data.get('ids')
				if not value:
					#if not data and not entered value then get default
					value = get_value_param_for_hook(param)
				#pram_server.append({"name":p, 'value': value, "attrs": param})
				pram_server.append({"name":p, 'value': value, "attrs": param})
				continue
			else:
				#value sent take precedence from value in doctype jasper_param_value
				value = data.get(p) or param.jasper_param_value
			pram.append({"name":p, 'value':[value]})
		resp = []
		#pram = (call_hook_for_param(doc, data, pram_server) or []) + pram
		res = call_hook_for_param(doc, data, pram_server) if pram_server else []
		for param in res:
			param.pop("attrs")
			#pvalue = param.get("value")
			#if isinstance(pvalue, dict) or isinstance(pvalue, list) or isinstance(pvalue, tuple):
			#	param["value"] = json.dumps(pvalue)
			print "pvalue {}".format(res)
			pram.append(param)
		copies = [_("Single"), _("Duplicated"), _("Triplicate")]
		for m in range(ncopies):
			if pram_copy_index >= 0:
				pram[pram_copy_index]['value'] = [copies[m]]
			if pram_copy_page_index >= 0:
				pram[pram_copy_page_index]['value'] = [str(m) + _(" of ") + str(ncopies)]
			result = self.run_async(path, pram, pformat=pformat)
			requestId = result.get('requestId')
			reqDbObj = {"data":{"result": result, "last_updated": frappe.utils.now(),'session_expiry': get_expiry_period()}}
			insert_jasper_reqid_record(requestId, reqDbObj)
			resp.append({"requestId":requestId, "status": result.get('status')})
		#TODO get reqId for check report state
		return resp

	def run_async(self, path, pram, pformat="pdf"):
		rs = ReportingService(self.session)
		rr = ReportExecutionRequest()
		rr.setReportUnitUri(path)
		rr.setOutputFormat(pformat)
		rr.setParameters(pram)
		rr.setAsync(True)
		try:
			req = rs.newReportExecutionRequest(rr)
			res = req.run().getResult("content")
			print "res from server 2: {}".format(res)
			res = json.loads(res)
			resp = prepareResponse(res, res.get("requestId"))
			resp["status"] = res.get("status")
			return resp
		except Exception as e:
			frappe.throw(_("Error in report %s, server error is: %s!!!" % (self.doc.jasper_report_name, e)))

	#see if report with requestID (reqId) is ready
	#send back to the client a dict: {reqId:[expIds]}
	def pollingReport(self, reqId, reqtime=""):
		res = []
		rs = ReportingService(self.session)
		rexecreq = rs.reportExecutionRequest(reqId)
		status = rexecreq.status().content
		print "status: {}".format(status)
		status = json.loads(status)
		if status.get("value") == "ready":
			detail = self.reportExecDetail(rexecreq)
			print "report detail: {}".format(detail)
			#detail = json.loads(detail)
			#res.append(prepareResponse(detail, reqId))
			res = prepareResponse(detail, reqId)
			#print "report detail res 2: {}".format(res)
			if res.get('status') == "not ready":
				res = prepareResponse({}, reqId)
			else:
				res["status"] = "ready"
		elif status.get("value") == "failed":
			frappe.throw(_("Error in report %s, server error is: %s!!!" % (self.doc.jasper_report_name, status['errorDescriptor'].get('message'))))
		else:
			#res.append(prepareResponse({}, reqId))
			res = prepareResponse({}, reqId)

		return res
	#rexecreq : ReportExecutionRequestBuilder instance
	#check if the report is ready and get the expids for ready reports
	def reportExecDetail(self, rexecreq):
		return rexecreq.executionDetails()

	#rs: ReportingService instance
	#get the report with reqId for the given expId
	def getReport(self, reqId, expId):
		rs = ReportingService(self.session)
		#print "getting report in getReport {} {}".format(reqId, expId)
		rexecreq = rs.reportExecutionRequest(reqId, expId)
		report = rexecreq.export().outputResource().getResult("content")
		return report

def update_jasper_reqid_record(reqId, data):
		#print "reqID update db {}".format(str(data['data']))
		frappe.db.sql("""update tabJasperReqids set data=%s, lastupdate=NOW()
			where reqid=%s""",(str(data['data']), reqId))
		# also add to memcache
		print "inserting reqId {0} data {1}".format(reqId, data['data'])
		jaspersession_set_value(reqId, data)
		frappe.db.commit()

def insert_jasper_reqid_record(reqId, data):
		frappe.db.sql("""insert into tabJasperReqids
			(reqid, data, lastupdate)
			values (%s , %s, NOW())""",
				(reqId, str(data['data'])))
		# also add to memcache
		print "inserting reqId {0} data {1}".format(reqId, data['data'])
		jaspersession_set_value(reqId, data)
		frappe.db.commit()

def prepareResponse(detail, reqId):
	res = {"requestId": reqId, "uri":detail.get("reportURI"), "reqtime": frappe.utils.now()}
	if detail.get("status") == "ready":
		ids = []
		for i in detail.get("exports"):
			if i.get("status") == "ready":
				id = i.get("id")
				outr = i.get("outputResource")
				ids.append({"id":id, "fileName": outr.get("fileName")})
			else:
				res['status'] = "not ready"
				break
		res["ids"] = ids
	return res

def prepareCollectResponse(resps):
	reqids = []
	status = "ready"
	for resp in reversed(resps):
		ncopies = []
		for r in resp:
			requestId = r.get('requestId')
			ncopies.append(requestId)
			#print "r is {}".format(r)
			#insert_jasper_reqid_record(requestId, {"data":r})
			if r.get('status') == "ready":
				continue
			status = "not ready"
		reqids.append(ncopies)
		#print "ncopies is {}".format(ncopies)
	res = make_internal_reqId(reqids, status)

	return res

def make_internal_reqId(reqids, status):
	intern_reqId = "intern_reqid_" + uuid.uuid4().hex
	reqtime = frappe.utils.now()
	reqDbObj = {"data":{"reqids": reqids, "last_updated": reqtime,'session_expiry': get_expiry_period(intern_reqId)}}
	insert_jasper_reqid_record(intern_reqId, reqDbObj)
	res = {"requestId": intern_reqId, "reqtime": reqtime, "status": status}
	return res

def get_jasper_reqid_data(reqId):
	data = get_jasper_data(reqId, get_from_db=get_jasper_reqid_data_from_db, args=[reqId])
	if not data:
		delete_jasper_session(reqId, "tabJasperReqids where reqid='%s'" % reqId)
	return frappe._dict({'data': data})

def get_jasper_reqid_data_from_db(*reqId):
	rec = frappe.db.sql("""select reqid, data
		from tabJasperReqids where
		TIMEDIFF(NOW(), lastupdate) < TIME(%s) and reqid=%s""", (get_expiry_period(reqId),reqId))
	return rec

"""
from ast import literal_eval
default_value = param.jasper_param_value
matchObj =re.match(r"^[\"'](.*)[\"']",default_value)
if matchObj:
	print "default_value with replace {}".format(matchObj.group(1))
	default_value = matchObj.group(1)
if default_value.startswith("(") or default_value.startswith("[") or default_value.startswith("{"):
	value = literal_eval(default_value)
	print "new param.jasper_param_value {}".format(value)
else:
	#this is the case when user enter "Administrator" and get translated to "'Administrator'"
	#then we need to convert to "Administrator" or 'Administrator'
	value = [str(default_value)]"""
"""from ast import literal_eval
default_value = param.jasper_param_value
#if re.match(r"['\"]|[\"']", default_value):
print "default_value {}".format(default_value)
if re.match(r"['\"]", default_value):
	matchObj = re.match(r"[\"'](.*)[\"']", default_value)
	print "matchObj {}".format(matchObj.group(1))
	default_value = literal_eval(default_value)
	#value = [literal_eval(new_value)]
if default_value.startswith("(") or default_value.startswith("[") or default_value.startswith("{"):
	value = literal_eval(default_value)
	print "new param.jasper_param_value {}".format(value)
else:
	#this is the case when user enter "Administrator" and get translated to "'Administrator'"
	#then we need to convert to "Administrator" or 'Administrator'
	value = [default_value]
"""
__author__ = 'luissaguas'
import jasper_erpnext_report.jasper_reports as jr
import logging, frappe
import uuid
import os
import thread

from frappe import _
from jasper_erpnext_report.utils.file import get_jasper_path, get_compiled_path
from jasper_erpnext_report.utils.report import prepareResponse, insert_jasper_reqid_record, get_jasper_reqid_data
from jasper_erpnext_report.utils.utils import call_hook_for_param, get_value_param_for_hook, get_expiry_period

#from pubsub import pub
#from Queue import Queue
#from threading import Thread
#import time

_logger = logging.getLogger(frappe.__name__)

print_format = ["docx", "ods", "odt", "rtf", "xls", "xlsx", "pptx", "xhtml", "pdf"]
#def jasper_run_report(path_jasper_file, reportName, reqId, data, params, conn, type):
def jasper_run_local_report(path, doc, data={}, params=[], async=True, pformat="pdf", ncopies=1, for_all_sites=1):
	#_logger.info("jasper_compile jrxml dir {0} destFileName {1}".format(jrxml, destFileName))
	pram_server = []
	hashmap = jr.HashMap()
	pram_copy_name = ""
	pram_copy_page_name = ""
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
			#a = ["'%s'" % t for t in data.get('name_ids')]
			value = "where name %s (%s)" % (param.param_expression, ",".join(a))
		elif is_copy == _("Is for copies"):
			#set the number of copies
			#indicate the index of param is for copies
			pram_copy_name = p
		elif is_copy == _("is for page number"):
			pram_copy_page_name = p
		elif is_copy == _("is for server hook"):
			#to alter like server reports
			#value = data.get('name_ids')
			value = data.get('ids')
			if not value:
				#if not data and not entered value then get default
				value = get_value_param_for_hook(param)
			pram_server.append({"name":p, 'value':value, "attrs": param})
			continue
			#value = call_hook_for_param(doc, data, param)
		else:
			#p = param.jasper_param_name
			#value sent take precedence from value in doctype jasper_param_value
			value = data.get(p) or param.jasper_param_value
		print "hashmap put param {} value {}".format(p, value)
		hashmap.put(p, value)
	path_join = os.path.join
	resp = []
	params = call_hook_for_param(doc, data, pram_server) if pram_server else []
	print "params in local {}".format(params)
	for param in params:
		p = param.get('name')
		value = param.get('value')
		hashmap.put(p, value)
	copies = [_("Single"), _("Duplicated"), _("Triplicate")]
	conn = "jdbc:mysql://" + (frappe.conf.db_host or 'localhost') + ":3306/" + frappe.local.site + "?user="+ frappe.conf.db_name +\
			"&password=" + frappe.conf.db_password
	reportName = getFileName(path)#data.get("report_name")
	jasper_path = get_jasper_path(for_all_sites)
	compiled_path = get_compiled_path(jasper_path, data.get("report_name"))
	outtype = print_format.index(pformat)
	for m in range(ncopies):
		if pram_copy_name:
			hashmap.put(pram_copy_name, copies[m])
			#print "hashmap 2 put param {} value {}".format(pram_copy_name, copies[m])
		if pram_copy_page_name:
			hashmap.put(pram_copy_page_name, str(m) + _(" of ") + str(ncopies))
			#print "hashmap 3 put param {} value {}".format(pram_copy_page_name, str(m) + _(" of ") + str(ncopies))
		reqId = uuid.uuid4().hex
		outputPath = path_join(compiled_path, reqId)
		frappe.create_folder(outputPath)
		sessionId = "local_report_" + reqId
		res = prepareResponse({"reportURI": os.path.relpath(outputPath, jasper_path) + os.sep + reportName + "." + pformat}, sessionId)
		#resp.append(res)
		res["status"] = None
		resp.append(res)#{"requestId":sessionId, "status": None}
		try:
			result = {"fileName": reportName + "." + pformat, "uri":outputPath + os.sep + reportName + "." + pformat, "last_updated": res.get("reqtime"), 'session_expiry': get_expiry_period(sessionId)}
			insert_jasper_reqid_record(sessionId, {"data":{"result":result, "last_updated": frappe.utils.now(),'session_expiry': get_expiry_period()}})
			thread.start_new_thread( _export_report, (compiled_path + os.sep, reportName, outputPath + os.sep, hashmap, conn, outtype, ) )
		except Exception as e:
			frappe.throw(_("Error in report %s, error is: %s!!!" % (doc.jasper_report_name, e)))
			#print "Error: unable to start thread"
	return resp

def _export_report(compiled_path, reportName, outputPath, hashmap, conn, outtype):
	export_report = jr.ExportReport()
	print "making 2 report compiled path {} reportName {} outputPath {} conn {} outtype {} hashmap {}".format(compiled_path, reportName, outputPath, conn, outtype, hashmap)
	export_report.export(compiled_path, reportName, outputPath, hashmap, conn, outtype)

def getLocalPolling(reqId, reqtime):
	#for reqId in reqIds:
	#rid = reqId[13:]
	data = get_jasper_reqid_data(reqId)
	if not data['data']:
		frappe.throw(_("No report for this reqid %s !!" % reqId[13:]))
	output_path = data['data']['result'].get("uri")
	#output_reqtime = data['data']['result'].get("reqtime")
	print "output_path {0} rid {1} data {2}".format(output_path, reqId, data)
	if os.path.exists(output_path):
		res = prepareResponse({"reportURI": data['data']['result'].get("uri"), "status":"ready", "exports":[{"status":"ready", "id":reqId, "outputResource":{"fileName": data['data']['result'].get("fileName")}}]}, reqId)
		res["status"] = "ready"
		print "local report exists {}".format(res)
		#res["path"] = data['data']['result'].get("path")
	else:
		res = prepareResponse({}, reqId)
	return res

def getLocalReport(reqId):
	data = get_jasper_reqid_data(reqId)
	if not data['data']:
		frappe.throw(_("No report for this reqid %s !!" % reqId))
	print "local file {}".format(data)
	output_path = data['data']['result'].get("uri")
	with open(output_path, mode='rb') as file:
		content = file.read()
	return content

def getFileName(file):
	index = file.rfind(os.sep) + 1
	name_ext = file[index:]
	return name_ext.split(".")[0]


"""def get_expiry_period():
	exp_sec = "00:10:00"
	#if len(exp_sec.split(':')) == 2:
	#	exp_sec = exp_sec + ':00'
	return exp_sec"""

"""
enclosure_queue = frappe.local.enclosure_queue = Queue()
#solution for live updates. Use this or tornado integration!
def downloadEnclosures(q):
	time.sleep(10)
	anObj = {"name":"luis", "idade":45}
	pub.sendMessage('rootTopic', arg1=123, q=q, arg3=anObj)
	#q.put()

@frappe.whitelist()
def conn_test():
	print '*** Main thread waiting'
	pub.subscribe(listener1, 'rootTopic')
	#worker = Thread(target=downloadEnclosures, args=(enclosure_queue,))
	#worker.setDaemon(True)
	#worker.start()
	downloadEnclosures(enclosure_queue)
	enclosure_queue.join()
	resp = enclosure_queue.get()
	print '*** Done'
	return resp

def listener1(arg1, q=None, arg3=None):
	q.put(arg3)
	q.task_done()
"""
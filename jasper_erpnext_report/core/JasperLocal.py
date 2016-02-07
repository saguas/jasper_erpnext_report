from __future__ import unicode_literals
__author__ = 'luissaguas'

from frappe import _
import frappe

from frappe.utils import cint

from jasper_erpnext_report.utils.file import get_jasper_path, get_file
from jasper_erpnext_report.utils.jasper_file_jrxml import get_compiled_path
import jasper_erpnext_report.utils.utils as utils
import jasper_erpnext_report.jasper_reports as jr
import JasperBase as Jb


#import uuid
import os, json


_logger = frappe.get_logger("jasper_erpnext_report")


print_format = ["docx", "ods", "odt", "rtf", "xls", "xlsx", "pptx", "html", "pdf"]

class JasperLocal(Jb.JasperBase):
	def __init__(self, doc=None):
		super(JasperLocal, self).__init__(doc, "local")

	def run_local_report_async(self, path, doc, data=None, params=None, pformat="pdf", ncopies=1, for_all_sites=0):
		from jasper_erpnext_report.core.FrappeTask import FrappeTask

		try:
			self.frappe_task = FrappeTask(frappe.local.task_id, None)
			cresp = self.prepare_report_async(path, doc, data=data, params=params, pformat=pformat, ncopies=ncopies, for_all_sites=for_all_sites)
			return [cresp]
		except Exception as e:
			frappe.throw(_("Error in report %s, error is: %s." % (doc.jasper_report_name, frappe.get_traceback())))

	def _run_report_async(self, path, doc, data=None, params=None, pformat="pdf", ncopies=1, for_all_sites=0):

		data = data or {}
		hashmap = jr.HashMap()
		pram, pram_server, copies = self.do_params(data, params, pformat, doc)
		pram_copy_index = copies.get("pram_copy_index", -1)
		pram_copy_page_index = copies.get("pram_copy_page_index", -1)

		path_join = os.path.join
		resp = []
		custom = doc.get("jasper_custom_fields")

		pram.extend(self.get_param_hook(doc, data, pram_server))

		self.populate_hashmap(pram, hashmap, doc.jasper_report_name)

		copies = [_("Original"), _("Duplicate"), _("Triplicate")]
		conn = ""
		if doc.query:
			conn = "jdbc:mysql://" + (frappe.conf.db_host or '127.0.0.1') + ":" + (frappe.conf.db_port or "3306") + "/" + frappe.conf.db_name + "?user="+ frappe.conf.db_name +\
				"&password=" + frappe.conf.db_password

		if not frappe.local.batch:
			batch = frappe._dict({})

			batch.batchReport = jr.BatchReport()

			batch.reportName = self.getFileName(path)
			batch.jasper_path = get_jasper_path(for_all_sites)
			batch.compiled_path = get_compiled_path(batch.jasper_path, data.get("report_name"))
			batch.outtype = print_format.index(pformat)
			batch.batchReport.setType(batch.outtype)
			batch.batchReport.setFileName(batch.reportName)
			#reqId = uuid.uuid4().hex
			reqId = frappe.local.task_id
			batch.outputPath = path_join(batch.compiled_path, reqId)
			frappe.create_folder(batch.outputPath)
			batch.batchReport.setOutputPath(batch.outputPath + os.sep + batch.reportName)
			batch.sessionId = "local_report_" + reqId

			res = self.prepareResponse({"reportURI": os.path.relpath(batch.outputPath, batch.jasper_path) + os.sep + batch.reportName + "." + pformat}, batch.sessionId)
			res["status"] = None
			res["report_name"] = data.get("report_name")
			resp.append(res)

			batch.batchReport.setTaskHandler(self.frappe_task)
			result = {"fileName": batch.reportName + "." + pformat, "uri":batch.outputPath + os.sep + batch.reportName + "." + pformat, "last_updated": res.get("reqtime"), 'session_expiry': utils.get_expiry_period(batch.sessionId)}
			self.insert_jasper_reqid_record(batch.sessionId, {"data":{"result":result, "report_name": data.get("report_name"), "last_updated": frappe.utils.now(),'session_expiry': utils.get_expiry_period()}})

			frappe.local.batch = batch

		lang = data.get("params", {}).get("locale", None) or "EN"
		cur_doctype = data.get("cur_doctype")
		ids = data.get('ids', [])[:]
		virtua = 0
		if doc.jasper_virtualizer:
			virtua = cint(frappe.db.get_value('JasperServerConfig', fieldname="jasper_virtualizer_pages")) or 0

		if custom and not frappe.local.fds:
			default = ['jasper_erpnext_report.jasper_reports.FrappeDataSource.JasperCustomDataSourceDefault']
			jds_method = utils.jasper_run_method_once_with_default("jasper_custom_data_source", data.get("report_name"), default)
			if jds_method.__name__ == 'JasperCustomDataSourceDefault':
				from jasper_erpnext_report.utils.utils import get_hook_module
				jscriptlet_module = get_hook_module("jasper_custom_data_source", data.get("report_name"))
				if jscriptlet_module:
					jds_method =  jscriptlet_module.get_data
			frappe.local.fds = jds_method

		for m in range(ncopies):
			if pram_copy_index != -1:
				values = pram[pram_copy_index].get("value","")
				pram_copy_name = pram[pram_copy_index].get("name","")
				if not values or not values[0]:
					hashmap.put(pram_copy_name, copies[m])
				else:
					hashmap.put(pram_copy_name, frappe.utils.strip(values[m], ' \t\n\r'))
			if pram_copy_page_index != -1:
				pram_copy_page_name = pram[pram_copy_page_index].get("name","")
				hashmap.put(pram_copy_page_name, str(m) + _(" of ") + str(ncopies))

			mparams = jr.HashMap()
			mparams.put("path_jasper_file", frappe.local.batch.compiled_path + os.sep)
			mparams.put("reportName", frappe.local.batch.reportName)
			mparams.put("outputPath", frappe.local.batch.outputPath + os.sep)
			mparams.put("params", hashmap)
			mparams.put("conn", conn)
			mparams.put("type", jr.Integer(frappe.local.batch.outtype))
			mparams.put("lang", lang)
			mparams.put("virtua", jr.Integer(virtua))
			#used for xml datasource
			mparams.put("numberPattern", frappe.db.get_default("number_format"))
			mparams.put("datePattern", frappe.db.get_default("date_format") + " HH:mm:ss")

			self._export_report(mparams, data.get("report_name"), data.get("grid_data"), frappe.local.batch.sessionId, cur_doctype, custom, ids, frappe.local.fds)
			if pram_copy_index != -1 and ncopies > 1:
				hashmap = jr.HashMap()
				self.populate_hashmap(pram, hashmap, doc.jasper_report_name)

		return resp

	def _export_report(self, mparams, report_name, grid_data, sessionId, cur_doctype, custom, ids, jds_method):
		from jasper_erpnext_report.jasper_reports.FrappeDataSource import _JasperCustomDataSource

		data = None
		cols = None
		fds = None

		if grid_data and grid_data.get("data", None):
			data, cols = self._export_query_report(grid_data)
			if not data or not cols:
				print "Error in report {}. There is no data.".format(report_name)
				frappe.throw(_("Error in report {}. There is no data.".format(report_name)))
				return

		if custom:
			jds = jds_method(ids, data, cols, cur_doctype)
			fds = jr.FDataSource(_JasperCustomDataSource(jds))

		#check if there is a scriptlet hook for this report.
		jscriptlet_method = utils.jasper_run_method_once_with_default("jasper_scriptlet", report_name, None)
		if jscriptlet_method:
			from jasper_erpnext_report.jasper_reports.ScriptletDefault import _JasperCustomScriptlet

			JasperScriptlet = jr.JavaFrappeScriptlet()
			JasperScriptlet.setFrappeScriptlet(_JasperCustomScriptlet(JasperScriptlet, jscriptlet_method(JasperScriptlet, ids, data, cols, cur_doctype, report_name)))
			mparams.get("params").put("REPORT_SCRIPTLET", JasperScriptlet)
		else:
			"""
				check if there is a scriptlet hook for this report in frappe-bench/sites/site_name/jasper_hooks folder.
				The folder have the following structure where jasper_hooks is the root(package):
					jasper_hooks/report name/hook name.py
					Example: jasper_hooks/Table 1 Custom/jasper_scriptlet.py -> where Table 1 Custom is the name of report and jasper_scriptlet.py
					is the name of the hook.
				Note: All the folders must have __init__.py to make it a package
				This strucutre is to help development. There is no need to make a frappe app only to control reports.
			"""
			from jasper_erpnext_report.utils.utils import get_hook_module
			from jasper_erpnext_report.jasper_reports.ScriptletDefault import _JasperCustomScriptlet

			jscriptlet_module = get_hook_module("jasper_scriptlet", report_name)
			if jscriptlet_module:
				JasperScriptlet = jr.JavaFrappeScriptlet()
				JasperScriptlet.setFrappeScriptlet(_JasperCustomScriptlet(JasperScriptlet, jscriptlet_module.get_data(JasperScriptlet, ids, data, cols, cur_doctype, report_name)))
				mparams.get("params").put("REPORT_SCRIPTLET", JasperScriptlet)

		frappe.local.batch.batchReport.addToBatch(mparams, data, cols, fds)



	def _export_query_report(self, grid_data):
		tables = []
		cols = []
		columnNames = grid_data.get("columns") or []
		data = grid_data.get("data") or []
		for obj in data:
			row = []
			for k in columnNames:
				value = str(obj.get(k.get("field")))
				if isinstance(value, basestring) and value == 'None':
					value = ''
				row.append(value)
			tables.append(row)

		for k in columnNames:
			cols.append(k.get("name"))

		return tables, cols

	def polling(self, reqId):
		data = self.get_jasper_reqid_data(reqId)
		if not data['data']:
			frappe.throw(_("No report for this requestid %s." % reqId[13:]))

		output_path = data['data']['result'].get("uri")
		# check if file already exists but also check if is size is > 0 because java take some time to write to file after
		# create the file in disc
		if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
			res = self.prepareResponse({"reportURI": output_path, "status":"ready", "exports":[{"status":"ready", "id":reqId, "outputResource":{"fileName": data['data']['result'].get("fileName")}}]}, reqId)
			res["status"] = "ready"
		else:
			res = self.prepareResponse({}, reqId)
		return res

	def getLocalReport(self, reqId):
		data = self.get_jasper_reqid_data(reqId)
		if not data['data']:
			frappe.throw(_("No report for this requestid %s." % reqId))
		output_path = data['data']['result'].get("uri")
		content = get_file(output_path, "rb")
		return content

	def getFileName(self, file):
		index = file.rfind(os.sep) + 1
		name_ext = file[index:]
		return name_ext.split(".")[0]


	def populate_hashmap(self, pram, hashmap, report_name):
		try:
			for p in pram:
				hashmap.put(p.get("name"), p.get("value")[0])
		except:
			frappe.throw(_("Error in report %s, there is a problem with value for parameter." % (report_name)))
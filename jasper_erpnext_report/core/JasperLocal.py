from __future__ import unicode_literals
__author__ = 'luissaguas'

from frappe import _
import frappe

from frappe.utils import cint

from jasper_erpnext_report.utils.file import get_jasper_path, get_compiled_path, get_file, get_html_reports_images_path
import jasper_erpnext_report.utils.utils as utils
import jasper_erpnext_report.jasper_reports as jr
import JasperBase as Jb

import logging
import uuid
import thread
import os

_logger = logging.getLogger(frappe.__name__)

print_format = ["docx", "ods", "odt", "rtf", "xls", "xlsx", "pptx", "html", "pdf"]

class JasperLocal(Jb.JasperBase):
	def __init__(self, doc={}):
		super(JasperLocal, self).__init__(doc)

	def run_local_report_async(self, path, doc, data={}, params=[], pformat="pdf", ncopies=1, for_all_sites=1):
		resps = []
		data = self.run_report_async(doc, data=data, params=params)
		if doc.jasper_report_type == "Form" or data.get('jasper_report_type', None) == "Form":
			ids = data.get('ids')
			for id in ids:
				data['ids'] = [id]
				resps.append(self._run_report_async(path, doc, data=data, params=params, pformat=pformat, ncopies=ncopies, for_all_sites=for_all_sites))
		else:
			resps.append(self._run_report_async(path, doc, data=data, params=params, pformat=pformat, ncopies=ncopies, for_all_sites=for_all_sites))
		cresp = self.prepareCollectResponse(resps)
		cresp["origin"] = "local"
		return [cresp]

	def _run_report_async(self, path, doc, data={}, params=[], pformat="pdf", ncopies=1, for_all_sites=1):
		hashmap = jr.HashMap()
		pram, pram_server, copies = self.do_params(data, params, pformat)
		pram_copy_index = copies.get("pram_copy_index", -1)
		pram_copy_page_index = copies.get("pram_copy_page_index", -1)

		path_join = os.path.join
		resp = []

		pram.extend(self.get_param_hook(doc, data, pram_server))

		try:
			for p in pram:
				hashmap.put(p.get("name"), p.get("value")[0])
		except:
			frappe.throw(_("Error in report %s, there is a problem with value for parameter in server hook: on_jasper_params." % (doc.jasper_report_name)))

		#copies = [_("Original"), _("Duplicated"), _("Triplicate")]
		copies = ["Original", "Duplicated", "Triplicate"]

		conn = ""
		if doc.query:
			conn = "jdbc:mysql://" + (frappe.conf.db_host or 'localhost') + ":3306/" + frappe.local.site + "?user="+ frappe.conf.db_name +\
				"&password=" + frappe.conf.db_password

		reportName = self.getFileName(path)
		jasper_path = get_jasper_path(for_all_sites)
		compiled_path = get_compiled_path(jasper_path, data.get("report_name"))
		outtype = print_format.index(pformat)

		lang = data.get("params", {}).get("locale", None) or "EN"

		virtua = 0
		if doc.jasper_virtualizer:
			virtua = cint(frappe.db.get_value('JasperServerConfig', fieldname="jasper_virtualizer_pages")) or 0

		for m in range(ncopies):
			if pram_copy_index != -1:
				pram_copy_name = pram[pram_copy_index].get("name","")
				hashmap.put(pram_copy_name, copies[m])
			if pram_copy_page_index != -1:
				pram_copy_page_name = pram[pram_copy_page_index].get("name","")
				hashmap.put(pram_copy_page_name, str(m) + _(" of ") + str(ncopies))
			reqId = uuid.uuid4().hex
			outputPath = path_join(compiled_path, reqId)
			frappe.create_folder(outputPath)
			sessionId = "local_report_" + reqId
			res = self.prepareResponse({"reportURI": os.path.relpath(outputPath, jasper_path) + os.sep + reportName + "." + pformat}, sessionId)
			res["status"] = None
			res["report_name"] = data.get("report_name")
			resp.append(res)#{"requestId":sessionId, "status": None}
			try:
				result = {"fileName": reportName + "." + pformat, "uri":outputPath + os.sep + reportName + "." + pformat, "last_updated": res.get("reqtime"), 'session_expiry': utils.get_expiry_period(sessionId)}
				self.insert_jasper_reqid_record(sessionId, {"data":{"result":result, "report_name": data.get("report_name"), "last_updated": frappe.utils.now(),'session_expiry': utils.get_expiry_period()}})

				mparams = jr.HashMap()
				mparams.put("path_jasper_file", compiled_path + os.sep)
				mparams.put("reportName", reportName)
				mparams.put("outputPath", outputPath + os.sep)
				mparams.put("params", hashmap)
				mparams.put("conn", conn)
				mparams.put("type", jr.Integer(outtype))
				mparams.put("lang", lang)
				mparams.put("virtua", jr.Integer(virtua))

				thread.start_new_thread(self._export_report, (mparams, data.get("report_name"), frappe.local.site, data.get("grid_data", None), ) )

			except Exception as e:
				frappe.throw(_("Error in report %s, error is: %s." % (doc.jasper_report_name, e)))
		return resp

	def _export_report(self, mparams, report_name, localsite, grid_data):
		try:
			outtype = mparams.get("type")
			outputPath = mparams.get("outputPath")
			fileName = mparams.get("reportName")
			if grid_data and grid_data.get("data", None):
				tables, cols = self._export_query_report(grid_data)
				mparams.put("tables", tables)
				mparams.put("columns", cols)

			export_report = jr.ExportReport(mparams)
			export_report.export()
			if outtype == 7:#html file
				content = get_file(outputPath + fileName + ".html")
				self.copy_images(content, outputPath, fileName, report_name, localsite)
		except Exception, e:
			#frappe.throw(_("Error in report {}, error is: {}".format(report_name, e)))
			print "Error in report 4 %s, error is: %s!!!" % (report_name, e)

	def _export_query_report(self, grid_data):
		tables = []
		cols = []
		columnNames = grid_data.get("columns") or []
		data = grid_data.get("data") or []
		for obj in data:
			row = []
			for k in columnNames:
				row.append(str(obj.get(k.get("field"))))
			tables.append(row)

		for k in columnNames:
			cols.append(k.get("name"))

		return tables, cols


	def copy_images(self, content, outputPath, fileName, report_name, localsite):
		from distutils.dir_util import copy_tree

		src = fileName + "." + "html_files"
		html_files = os.path.join(outputPath, src)
		report_path = self.get_html_path(report_name, localsite=localsite, content=content)
		dst = get_html_reports_images_path(report_path, where=src)
		copy_tree(html_files, dst)

	def polling(self, reqId):
		data = self.get_jasper_reqid_data(reqId)
		if not data['data']:
			frappe.throw(_("No report for this requestid %s." % reqId[13:]))
		output_path = data['data']['result'].get("uri")
		if os.path.exists(output_path):
			res = self.prepareResponse({"reportURI": data['data']['result'].get("uri"), "status":"ready", "exports":[{"status":"ready", "id":reqId, "outputResource":{"fileName": data['data']['result'].get("fileName")}}]}, reqId)
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
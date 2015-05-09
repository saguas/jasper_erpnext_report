from __future__ import unicode_literals
__author__ = 'luissaguas'

from frappe import _
import frappe

from frappe.utils import cint

from jasper_erpnext_report.utils.file import get_jasper_path, get_file, get_html_reports_images_path
from jasper_erpnext_report.utils.jasper_file_jrxml import get_compiled_path
import jasper_erpnext_report.utils.utils as utils
import jasper_erpnext_report.jasper_reports as jr
import JasperBase as Jb

import uuid
import thread
import os

print_format = ["docx", "ods", "odt", "rtf", "xls", "xlsx", "pptx", "html", "pdf"]

class JasperLocal(Jb.JasperBase):
	def __init__(self, doc=None):
		super(JasperLocal, self).__init__(doc)

	def run_local_report_async(self, path, doc, data=None, params=None, pformat="pdf", ncopies=1, for_all_sites=0):
		"""
		resps = []
		data = self.run_report_async(doc, data=data, params=params)
		print "doc.get is_doctype_id {}".format(data.get("is_doctype_id", None))
		if (doc.jasper_report_type == "Form" or data.get('jasper_report_type', None) == "Form") and not data.get("is_doctype_id", None):
			ids = data.get('ids')
			for id in ids:
				data['ids'] = [id]
				resps.append(self._run_report_async(path, doc, data=data, params=params, pformat=pformat, ncopies=ncopies, for_all_sites=for_all_sites))
		else:
			resps.append(self._run_report_async(path, doc, data=data, params=params, pformat=pformat, ncopies=ncopies, for_all_sites=for_all_sites))
		cresp = self.prepareCollectResponse(resps)
		cresp["origin"] = "local"
		return [cresp]
		"""
		cresp = self.prepare_report_async(path, doc, data=data, params=params, pformat=pformat, ncopies=ncopies, for_all_sites=for_all_sites)
		cresp["origin"] = "local"
		return [cresp]

	def _run_report_async(self, path, doc, data=None, params=None, pformat="pdf", ncopies=1, for_all_sites=0):
		data = data or {}
		hashmap = jr.HashMap()
		pram, pram_server, copies = self.do_params(data, params, pformat)
		pram_copy_index = copies.get("pram_copy_index", -1)
		pram_copy_page_index = copies.get("pram_copy_page_index", -1)

		path_join = os.path.join
		resp = []

		pram.extend(self.get_param_hook(doc, data, pram_server))

		self.populate_hashmap(pram, hashmap, doc.jasper_report_name)

		copies = [_("Original"), _("Duplicated"), _("Triplicate")]
		conn = ""
		if doc.query:
			conn = "jdbc:mariadb://" + (frappe.conf.db_host or 'localhost') + ":" + (frappe.conf.db_port or "3306") + "/" + frappe.conf.db_name + "?user="+ frappe.conf.db_name +\
				"&password=" + frappe.conf.db_password
			#conn = "jdbc:mysql://" + (frappe.conf.db_host or 'localhost') + ":" + (frappe.conf.db_port or "3306") + "/" + frappe.local.site + "?user="+ frappe.conf.db_name +\
				#"&password=" + frappe.conf.db_password
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
				values = pram[pram_copy_index].get("value","")
				pram_copy_name = pram[pram_copy_index].get("name","")
				if not values or not values[0]:
					hashmap.put(pram_copy_name, copies[m])
				else:
					hashmap.put(pram_copy_name, frappe.utils.strip(values[m], ' \t\n\r'))
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
			resp.append(res)
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
				#used for xml datasource
				mparams.put("numberPattern", frappe.db.get_default("number_format"))
				mparams.put("datePattern", frappe.db.get_default("date_format") + " HH:mm:ss")

				thread.start_new_thread(self._export_report, (mparams, data.get("report_name"), frappe.local.site, data.get("grid_data", None), sessionId) )
				if pram_copy_index != -1 and ncopies > 1:
					hashmap = jr.HashMap()
					self.populate_hashmap(pram, hashmap, doc.jasper_report_name)

			except Exception as e:
				frappe.throw(_("Error in report %s, error is: %s." % (doc.jasper_report_name, e)))
		return resp

	def _export_report(self, mparams, report_name, localsite, grid_data, sessionId):
		try:
			outtype = mparams.get("type")
			outputPath = mparams.get("outputPath")
			fileName = mparams.get("reportName")

			data = None
			cols = None
			if grid_data and grid_data.get("data", None):
				data, cols = self._export_query_report(grid_data)
				if not data or not cols:
					print "Error in report {}. There is no data.".format(report_name)
					return
			export_report = jr.ExportReport(mparams)
			export_report.export(data, cols)
			if outtype == 7:#html file
				content = get_file(outputPath + fileName + ".html")
				self.copy_images(content, outputPath, fileName, report_name, localsite)
		except Exception, e:
			print "Error in report %s, error is: %s" % (report_name, e)
			utils.jaspersession_set_value(sessionId, e)
			#frappe.throw(_("Error in report {}, error is: {}".format(report_name, e)))

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


	def copy_images(self, content, outputPath, fileName, report_name, localsite):
		from distutils.dir_util import copy_tree

		src = fileName + "." + "html_files"
		html_files = os.path.join(outputPath, src)
		#this is a report without folder html_files
		if not os.path.exists(html_files):
			return
		report_path = self.get_html_path(report_name, localsite=localsite, content=content)
		dst = get_html_reports_images_path(report_path, where=src)
		copy_tree(html_files, dst)

	def polling(self, reqId):
		data = self.get_jasper_reqid_data(reqId)
		if not data['data']:
			frappe.throw(_("No report for this requestid %s." % reqId[13:]))
		output_path = data['data']['result'].get("uri")
		# check if file already exists but also check if is size is > 0 because java take some time to write to file after
		# create the file in disc
		error = utils.jaspersession_get_value(reqId)
		if error:
			print "request with error {}".format(reqId)
			res = self.prepareResponse({}, reqId)
			res[error] = error
			return res
		if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
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


	def populate_hashmap(self, pram, hashmap, report_name):
		try:
			for p in pram:
				hashmap.put(p.get("name"), p.get("value")[0])
		except:
			frappe.throw(_("Error in report %s, there is a problem with value for parameter." % (report_name)))
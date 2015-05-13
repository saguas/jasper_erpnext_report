from __future__ import unicode_literals
__author__ = 'luissaguas'
from frappe import _
import frappe

import json, os

from frappe.utils import cint
from jasper_erpnext_report.utils.file import write_file, get_extension
import jasper_erpnext_report.utils.utils as utils
import JasperServer as Js, JasperLocal as Jl, JasperBase as Jb
from jasper_erpnext_report.utils.cache import redis_transation
from jasper_erpnext_report import jasperserverlib

from io import BytesIO
from PyPDF2 import PdfFileMerger
import cStringIO
import zipfile, hashlib

_logger = frappe.get_logger("jasper_erpnext_report")

class JasperRoot(Jb.JasperBase):
	def __init__(self, doc=None):
		self.jps = None
		self.jpl = None
		frappe.local.jasper_session_obj = self
		super(JasperRoot, self).__init__(doc)

	def get_server(self, origin):
		if origin == "server":
			if not self.jps:
				self.jps = Js.JasperServer(self.doc)
				return self.jps
		elif origin == "local":
			if not self.jpl:
				self.jpl = Jl.JasperLocal(self.doc)
				return self.jpl

	#called in jasperserverconfig.py at the save button was pushed. Just save the data
	def config(self):
		_logger.info("JasperServerSession update_cache self.doc {}".format(self.doc))
		if not self.doc:
			frappe.throw(_("Something was wrong, there is no document." ))

		from jasper_erpnext_report import pyjnius
		print "use local and pyjnius local? {} pyjnius {}".format(self.use_local(), pyjnius)
		if self.use_local() and not pyjnius:
			frappe.throw(_("You don't have local server. Install python module pyjnius first." ))

		if self.data["data"]:
			self.update(force_cache=True, force_db=True)
		else:
			#delete all db old sessions if exist
			self.delete_jasper_session()
			self.createJasperSession()

		return

	def login(self):
		self.get_server("server")
		self.jps.login()
		if self.doc.import_all_reports:
			self.jps.import_all_jasper_reports(self.doc)
		if self.jps.is_login:
			self.doc.jasper_server_name = self._get_server_info(force=True)
		else:
			self.doc.jasper_server_name = "Not connected!"

		self.update(force_cache=True, force_db=True)
		return self.doc.jasper_server_name

	def _get_server_info(self, force=False):
		if not force and self.doc.jasper_server_name:
			return self.doc.jasper_server_name
		return self.jps.get_server_info()

	def _get_reports_list(self, filters_report=None, filters_param=None, force=False, cachename="report_list_all", update=False):
		ret = self.get_reports_list_from_db(filters_report=filters_report, filters_param=filters_param)
		#check to see if there is any report by now. If there are reports don't check the server
		#jasperserverlib sign if it was imported jasperserver, a library to connect to the jasperreport server
		if self.user == "Administrator" and ret is None and self.use_server() and jasperserverlib:
			#called from client. Don't let him change old reports attributes
			import_only_new = self.data['data'].get('import_only_new')
			self.data['data']['import_only_new'] = 1
			self.get_server("server")
			self.jps.import_all_jasper_reports(self.data['data'], force=force)
			self.data['data']['import_only_new'] = import_only_new
			#could be recursive but there is no need for resume again because decorator
			ret = self.get_reports_list_from_db(filters_report=filters_report, filters_param=filters_param)

		#in_transation = frappe.utils.cint(frappe.__version__.split(".", 1)[0]) > 4
		in_transation = utils.getFrappeVersion().major > 4

		if ret:
			ptime = self.data['data'].get('jasper_polling_time')
			ret['jasper_polling_time'] = ptime

		if ret and not update:
			data = utils.insert_list_all_memcache_db(ret, cachename=cachename, in_transation=in_transation)
		elif ret:
			data = utils.update_list_all_memcache_db(ret, cachename=cachename, in_transation=in_transation)
		else:
			data = {"data":{"origin": self.get_report_origin()}}

		return data

	def get_reports_list_for_all(self):
		if self.sid == 'Guest':
			return None
		data = {}
		#dirt = utils.jaspersession_get_value("report_list_dirt_all")
		#dirt = self.is_dirt("report_list_dirt_all")
		#dirt = self.is_cache_dirt("report_list_dirt_all", "user:" + self.user + "_report_list_all")
		dirt = utils.jaspersession_get_value("report_list_dirt_all") or False

		#dirt if redis not cache
		if not dirt:
			#data = utils.get_jasper_session_data_from_cache("user:" + self.user + "_report_list_all")
			#if not data:

			data = utils.get_jasper_session_data_from_cache("report_list_all")
			#if data:
			#	dirt = utils.jaspersession_get_value("report_list_dirt_all") or frappe.utils.now()
			#	all_last_update = data.get('last_updated')
			#	time_diff = frappe.utils.time_diff_in_seconds(dirt, all_last_update)
			#	if time_diff > 0:
			#		data = None
			#else:
			#	if not self.check_server_status():
			#		self.remove_server_docs(data)
			#	return data
		#if for some reason there is no cache get it from db
		if not data:
			#frappe.cache().delete_value("jasper:report_list_all")
		#	frappe.cache().delete_value("jasper:user:" + self.user + "_report_list_all")
			r_filters=["`tabJasper Reports`.jasper_doctype is NULL", "`tabJasper Reports`.report is NULL"]
			ldata = self._get_reports_list(filters_report=r_filters)
			cached = redis_transation(ldata, "report_list_all")
			if ldata:
				data = ldata.get("data", None)
			if cached and data:
				utils.jaspersession_set_value("report_list_dirt_all", False)
				#utils.jaspersession_set_value("report_list_dirt_all", frappe.utils.now())
				#utils.jaspersession_set_value("report_list_dirt_doc", frappe.utils.now())
				#utils.jaspersession_set_value("report_list_dirt_doc", False)

		if data:
			#utils.jaspersession_set_value("report_list_dirt_all", frappe.utils.now())
			data.pop('session_expiry', None)
			data.pop('last_updated', None)

			self.filter_perm_roles(data)
			if not self.check_server_status():
				self.remove_server_docs(data)
			try:
				version = utils.getFrappeVersion().major
				if version >= 5:
					from jasper_erpnext_report.utils.jasper_email import is_email_enabled
					acc = cint(is_email_enabled())
				else:
					acc = cint(frappe.db.get_single_value("Outgoing Email Settings", "enabled"))

				data['mail_enabled'] = acc
			except:
				data['mail_enabled'] = "disabled"

			#utils.insert_list_all_memcache_db(data, cachename="user:" + self.user + "_report_list_all")
			#utils.jaspersession_set_value("user:" + self.user + "_report_list_all", frappe.utils.now())

		return data

	"""
	def is_cache_dirt(self, lstdirt, what):
		#data = utils.get_jasper_session_data_from_cache(what)
		#if data:
		is_dirt = False
		user_last_update = utils.jaspersession_get_value(what)
		dirt = utils.jaspersession_get_value(lstdirt)
		if not user_last_update or not dirt:
			utils.jaspersession_set_value(what, frappe.utils.now())
			return False
		#user_last_update = data.get('last_updated')
		#user_last_update = data
		time_diff = frappe.utils.time_diff_in_seconds(dirt, user_last_update)
		#print "what {} dirt {} last_update {} time_diff {}".format(what, dirt, user_last_update, time_diff)
		if time_diff >= 0:
			is_dirt = True

		return is_dirt
	"""

	def remove_server_docs(self, data):
		toremove = []
		removed = 0
		for k,v in data.iteritems():
			if isinstance(v, dict):
				origin = v.get("jasper_report_origin", None)
				if origin == "JasperServer":
					toremove.append(k)
					removed = removed + 1
		for k in toremove:
			data.pop(k, None)
		data['size'] = data['size'] - removed

	def check_server_status(self):
		if self.use_server():
			self.get_server("server")
		else:
			return False
		return self.jps.is_login

	def get_reports_list(self, doctype, docnames, report):
		if not doctype and not report:
			frappe.throw(_("You need to provide the doctype name or the report name."))
		if docnames:
			docnames = json.loads(docnames)
		else:
			docnames = []

		new_data = {'size': 0}
		if frappe.local.session['sid'] == 'Guest':
			return None

		#dirt = utils.jaspersession_get_value("report_list_dirt_doc")
		data = {}
		#dirt = self.is_cache_dirt("report_list_dirt_doc", "user:" + self.user + "_report_list_doctype")
		dirt = utils.jaspersession_get_value("report_list_dirt_doc")
		if not dirt:
			#data = utils.get_jasper_session_data_from_cache("user:" + self.user + "_report_list_doctype")
			#if not data:

			data = utils.get_jasper_session_data_from_cache("report_list_doctype")

		if not data or not self.check_docname(data, doctype, report):
			#frappe.cache().delete_value("jasper:report_list_doctype")
			#frappe.cache().delete_value("jasper:user:" + self.user + "_report_list_doctype")
			if doctype:
				r_filters={"jasper_doctype": doctype}
			else:
				r_filters={"report": report}
			update = False if not data else True
			ldata = self._get_reports_list(filters_report=r_filters, cachename="report_list_doctype", update=update)
			cached = redis_transation(ldata, "report_list_doctype")
			if ldata:
				data = ldata.get("data", None)
			if cached and data and dirt:
				utils.jaspersession_set_value("report_list_dirt_doc", False)

		if data and self.check_docname(data, doctype, report):
			data.pop('session_expiry',None)
			data.pop('last_updated', None)
			new_data = self.doc_filter_perm_roles(doctype or report, data, docnames)
			#print "report list dirt {} report {} docnames {} doctype {}".format(dirt, report, docnames, data)
			#if the list was updated or inserted
			#if dirt:
			#	utils.jaspersession_set_value("report_list_dirt_doc", False)
				#utils.jaspersession_set_value("user:" + self.user + "_report_list_doctype", frappe.utils.now())

		if not self.check_server_status():
			self.remove_server_docs(new_data)

		#new_data['mail_enabled'] = cint(frappe.db.get_single_value("Outgoing Email Settings", "enabled"))
		#utils.insert_list_all_memcache_db(new_data, cachename="user:" + self.user + "_report_list_doctype")
		return new_data

	def report_polling(self, data):
		if not data:
			frappe.throw(_("There is no report to poll"))
		if isinstance(data, basestring):
			data = json.loads(data)
		self.validate_ticket(data)
		reqIds = data.get("reqIds")
		pformat = data.get("pformat")
		if data.get("origin") == "local":
			self.get_server("local")
			report_name = self.get_jasper_reqid_data(reqIds[0])
			result = self.jpl.report_polling_base(reqIds[0], report_name)
		else:
			#check only one requestId
			self.get_server("server")
			report_name = self.get_jasper_reqid_data(reqIds[0])
			result = self.jps.report_polling_base(reqIds[0], report_name)
		result[0]["pformat"] = pformat

		return result

	def run_report(self, data, docdata=None):
		doctype = data.get('doctype')
		rdoc = frappe.get_doc(doctype, data.get('report_name'))

		#call hook before run the report
		utils.call_hook_for_param(rdoc, "jasper_before_run_report", data)

		rtype = rdoc.get("jasper_report_type")
		if data.get("fortype").lower() == "doctype" and rtype in ("List", "Form"):
			for docname in data.get('name_ids', []) or []:
				if not utils.check_frappe_permission(rdoc.jasper_doctype, docname, ptypes=("read", "print")):
					raise frappe.PermissionError(_("No {0} permission for document {1} in doctype {3}.").format("read or print", docname, rdoc.jasper_doctype))
			#if user can read doc it is possible that can't print it! Just uncheck Read permission in doctype Jasper Reports
			#if not self.check_jasper_doc_perm(rdoc.jasper_roles):
		if not utils.check_frappe_permission("Jasper Reports", data.get('report_name', ""), ptypes="read"):
			raise frappe.PermissionError(_("You don't have print permission."))

		params = rdoc.jasper_parameters
		origin = rdoc.jasper_report_origin.lower()
		pformat = data.get('pformat')
		#try:
		ncopies = get_copies(rdoc, pformat)
		if origin == "localserver":
			path = rdoc.jrxml_root_path
			self.get_server("local")
			if not path:
				frappe.throw(_("%s: Import first a jrxml file." % rdoc.name))
			for_all_sites = rdoc.jasper_all_sites_report
			result = self.jpl.run_local_report_async(path, rdoc, data=data, params=params, pformat=pformat, ncopies=ncopies, for_all_sites=for_all_sites)
		else:
			path = rdoc.jasper_report_path
			self.get_server("server")
			if not self.jps.is_login:
				frappe.msgprint(_("Jasper Server, login error."))
				return

			result = self.jps.run_remote_report_async(path, rdoc, data=data, params=params, pformat=pformat, ncopies=ncopies)
		result[0]["pformat"] = pformat

		return result

	def get_report_server(self, data):
		#check if this requestId is older than last timeout
		self.validate_ticket(data)
		d = self.get_jasper_reqid_data(data.get('requestId'))
		report_name = d['data'].get("report_name")
		if not d:
			frappe.throw(_("Report Not Found."))
		"""
		reqids represent the ids of documents.
		Example:
		if my document is of type (Report for) form and in list view i check more than one document, say n,
		then it will ask the server for n documents at once
		and for every document it will ask for one, two or tree copies
		as may have single, duplicated or triplicated checked.
		"""
		reqids = d['data'].get('reqids')
		content = []
		fileName = None
		try:
			for ids in reqids:
				"""
				ask the server for one, two or tree documents if single, duplicated or triplicated respectively
				"""
				for id in ids:
					report = self.get_jasper_reqid_data(id)
					rdata = report['data'].get('result')
					reqId = [rdata.get("requestId")]
					expId = rdata.get("ids")
					fileName = expId[0].get("fileName", None)
					print "_get_report id 2 {} fileName {}".format(id, frappe.utils.pprint_dict(report, level=3))
					file_ext = get_extension(fileName)
					#this is for another situation
					rid_len = 1
					if not any("local_report" in r for r in reqId):
						eid_len = len(expId)
						self.get_server("server")
						if not self.jps.is_login:
							frappe.msgprint(_("Jasper Server, login error."))
							return
						#if lens not equal then process only the first
						if rid_len == eid_len:
							for i in range(rid_len):
								c = self.jps.getReport(reqId[i], expId[i].get('id'))
								content.append(c)
								if file_ext == "html":
									hash_obj = hashlib.md5(c)
									self.html_hash = hash_obj.hexdigest()
									self.getAttachments(reqId[i], expId[i].get('id'), expId[i], report_name)
									break

						else:
							"""
							This situation only occurs when i get multiples sub documents (len expId > 1) for one request (document).
							This is jasper issue and it is here for future updates
							"""
							c = self.jps.getReport(reqId[0], expId[0].get('id'))
							content.append(c)
							if file_ext == "html":
								hash_obj = hashlib.md5(c)
								self.html_hash = hash_obj.hexdigest()
								self.getAttachments(reqId[0], expId[0].get('id'), expId[0], report_name)
					else:
						self.get_server("local")
						for i in range(rid_len):
							c = self.jpl.getLocalReport(reqId[i])
							content.append(c)
							if file_ext == "html":
								hash_obj = hashlib.md5(c)
								self.html_hash = hash_obj.hexdigest()
								break
		except Exception as e:
			return frappe.msgprint(_("There is no report, try again later. Error: {}".format(e)))

		return fileName, content, report_name

	def getAttachments(self, reqId, expId, expIdObj, report_name):
		for attach in expIdObj.get('attachments',[]):
			attachFileName = attach.get("fileName")
			content = self.jps.getAttachment(reqId, expId, attachFileName)
			from jasper_erpnext_report.utils.file import get_html_reports_images_path, get_html_reports_path
			report_path = get_html_reports_path(report_name, hash=self.html_hash)
			image_path = get_html_reports_images_path(report_path)
			write_file(content.content, os.path.join(image_path, attachFileName), "wb")



	#pages is an array of pages ex. [2,4,5]
	def make_pdf(self, fileName, content, pformat, merge_all=True, pages=None):
		if fileName:
			fileName = fileName[fileName.rfind(os.sep) + 1:]
			output = cStringIO.StringIO()
			file_name = fileName.replace(" ", "-").replace("/", "-")
			if pformat=="pdf" and merge_all == True:
				merger = PdfFileMerger()
				for n in range(len(content)):
					merger.append(BytesIO(content[n]))
				merger.write(output)
			elif pformat=="pdf":
				merger = PdfFileMerger()
				for page in pages:
					merger.append(BytesIO(content[page]))
				merger.write(output)
			else:
				fname = file_name.split(".")
				myzip = zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED)
				try:
					pgs = range(len(content)) if pages is None else pages
					for n in pgs:
						myzip.writestr(fname[0] + "_" + str(n) + "." + fname[1], content[n])
				finally:
					myzip.close()
				file_name = fname[0] + ".zip"
			return file_name, output
		else:
			frappe.msgprint(_("There is no report."))

	def prepare_file_to_client(self, file_name, output):
		frappe.local.response.filename = "{name}".format(name=file_name)
		frappe.local.response.filecontent = output
		frappe.local.response.type = "download"

def get_copies(rdoc, pformat):
	"""
	make copies (Single, Duplicated or Triplicated) only for pdf format
	"""
	#copies = [_("Original"), _("Duplicated"), _("Triplicate")]
	copies = ["Original", "Duplicated", "Triplicate"]
	#return copies.index(_(rdoc.jasper_report_number_copies)) + 1 if pformat == "pdf" else 1
	return copies.index(rdoc.jasper_report_number_copies) + 1 if pformat == "pdf" else 1
from __future__ import unicode_literals
__author__ = 'luissaguas'
from frappe.model.document import Document

from frappe import _
import frappe
from io import BytesIO
import uuid, os

import jasper_erpnext_report.utils.utils as utils
from jasper_erpnext_report.utils.file import get_file, get_html_reports_images_path
from jasper_erpnext_report.utils.file import JasperXmlReport, get_html_reports_path

_logger = frappe.logger("jasper_erpnext_report")

jasper_fields_not_supported = ["parent", "owner", "modified_by", "parenttype", "parentfield", "docstatus", "doctype", "name", "idx"]

class JasperBase(object):
	def __init__(self, doc=None, origin=None):
		doc = doc or {}
		if isinstance(doc, Document):
			self.doc = frappe._dict(doc.as_dict())
		else:
			self.doc = frappe._dict(doc)
		self.user = frappe.local.session["user"]
		self.sid = frappe.local.session["sid"]
		self.frappe_task = None
		self.reset_data_session()
		self.report_html_path = None
		self.html_hash = None
		self.report_origin = origin
		self.resume()

	def reset_data_session(self):
		self.data = frappe._dict({'data': frappe._dict({})})

	def in_jasper_session(self):
		return False

	def use_server(self):
		try:
			doc_jasper_server = self.doc.use_jasper_server.lower()
			return doc_jasper_server == "jasperserver only" or doc_jasper_server == "both"
		except:
			return False

	def use_local(self):
		doc_jasper_server = self.doc.use_jasper_server.lower()
		return doc_jasper_server == "local jrxml only" or doc_jasper_server == "both"

	def get_report_origin(self):
		try:
			origin = self.doc.use_jasper_server.lower()
		except:
			origin = "localserver"
		return origin

	def get_jasperconfig_from_db(self):
		self.doc = frappe.db.get_value('JasperServerConfig', None, "*", ignore=True, as_dict=True) or frappe._dict({})
		self.createJasperSession()

	def resume(self):
		if self.data['data']:
			return
		data = self.get_jasper_session_data()
		if data:
			self.data = frappe._dict({'data': data, 'user':data.get("user")})
		else:
			#if data session expire or not exist get from db the data, in this case no cookies!
			self.get_jasperconfig_from_db()

		if not self.doc:
			self.doc = self.data['data'] or frappe._dict({})

	def get_jasper_session_data(self):
		data = utils.get_jasper_data("jaspersession")
		if not data:
			self.delete_jasper_session()
		return data

	def createJasperSession(self):
		if self.user!="Guest":
			self.update_data_cache()
			self.data['data']['session_expiry'] = utils.get_expiry_period()
			self.insert_jasper_session_record()
			frappe.db.commit()

	def update_data_cache(self):
		self.data['data'] = {letter: i for letter,i in self.doc.iteritems() if letter not in jasper_fields_not_supported}
		self.data['user'] = self.user
		self.data['data']['last_updated'] = frappe.utils.now()

	def insert_jasper_session_record(self):
		frappe.db.sql("""insert into tabJasperSessions
			(sessiondata, user, lastupdate, status)
			values (%s , %s, NOW(), 'Active')""",
				(str(self.data['data']), self.data['user']))
		# also add to memcache
		utils.jaspersession_set_value("jaspersession", self.data)
		utils.jaspersession_set_value("last_db_jasper_session_update", frappe.utils.now())

	def delete_jasper_session(self):
		utils.delete_jasper_session("jaspersession")

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
		last_updated = utils.jaspersession_get_value("last_db_jasper_session_update")
		time_diff = frappe.utils.time_diff_in_seconds(now, last_updated) if last_updated else None

		# database persistence is secondary, don't update it too often
		updated_in_db = False
		if force_db or (time_diff==None) or (time_diff > 300):
			frappe.db.sql("""update tabJasperSessions set sessiondata=%s,
				lastupdate=NOW() where TIMEDIFF(NOW(), lastupdate) < TIME(%s) and status='Active'""" , (str(self.data['data']), utils.get_expiry_period()))
			utils.jaspersession_set_value("last_db_jasper_session_update", now)
			updated_in_db = True
			frappe.db.commit()

		# set in memcache
		utils.jaspersession_set_value("jaspersession", self.data)

		return updated_in_db

	def get_ask_params(self, data):
		pram = []
		params = data.get("params", None) or {}
		for k,v in params.iteritems():
			pram.append({"name":k, 'value':[v]})
		return pram

	def get_param_hook(self, doc, data, pram_server):
		"""
		Set a 'on_jasper_params' hook for each report that you want to set parameters of type 'Is for server hook', like this one:
		on_jasper_params = {
			"Cherry Local": "jasper_erpnext_report.utils.utils.testHookReport"
		}
		HOOK: Must return a list of objects.
		Some examples are:

		def on_jasper_params(doc, data=None, params=None):
			a = []
			for param in params:
				if param.get("name") == "idade":
					a.append({"name": param.get("name"), "value": 35.6})
				else:
					#a.append({"name": param.get("name"), "value":['luisfmfernandes@gmail.com'], "param_type": "is for where clause"})
					a.append({"name": param.get("name"), "value":['luisfmfernandes@gmail.com']})
				#a.append({"name":param.get("name"), "value": ["Administrator", "luisfmfernandes@gmail.com"], "param_type": "Is for where clause"})
			#a.append({"name": params[0].get("name"), "value":'select name, email from tabUser where name in ("luisfmfernandes@gmail.com")'})
			#a.append({"name": params[0].get("name"), "value":['Administrator', 'Guest'], "param_type": "is for where clause"})
			#a.append({"name": params[0].get("name"), "value":['Guest', 'Administrator']})
			#a.append({"name": params[0].get("name"), "value":345})

			return a
		"""
		pram = []
		#res = utils.call_hook_for_param(doc, "on_jasper_params", data, pram_server) if pram_server else []
		res = utils.call_hook_for_param_with_default(doc, "on_jasper_params", data, pram_server) if pram_server else []
		if res is None:
			frappe.throw(_("Error in report %s, there is no value for parameter in server hook: on_jasper_params." % (doc.jasper_report_name)))
		for param in res:
			param.pop("attrs", None)
			param_type = param.pop("param_type", None)
			if param_type and param_type.lower() == "is for where clause":
				param.setdefault("param_expression", "In")
				value = self.get_where_clause_value(param.get("value", None), frappe._dict(param))
				if not value:
					frappe.throw(_("Error in report %s, there is no value for parameter %s in server hook: on_jasper_params." % (doc.jasper_report_name, param.get("name", ""))))

				param["value"] = [value]
				param.pop("param_expression", None)

			value = param.get("value",None)
			if value is not None and not isinstance(value, list):
				value = [value]
			try:
				"""
				If number returned then convert number to string.
				"""
				number = value[0]
				int(number)
				param["value"] = [str(value[0])]
			except ValueError:
				"""
				If not number returned.
				"""
				param["value"] = value
			pram.append(param)

		return pram

	def get_param_values(self, values):

		if values and isinstance(values, basestring):
			val = values.replace("\"","").replace("'","").split(",")
			if len(val)>1:
				value = val
			else:
				value = [values]
		else:
			if isinstance(values, (list, tuple)) and len(values)>1:
				value = values
			else:
				value = [values]

		return value

	def do_params(self, data, params, pformat, doc):
		pram = []
		copies = {}
		pram_server = []
		#used_ids = False

		for param in params:
			is_copy = param.is_copy.lower()
			p = param.jasper_param_name
			value = ""
			if is_copy == "is for where clause":
				value = self.get_where_clause_value(data.get('ids', []), param)
				if not value:
					"""
					Check if the ids was sended by asked parameters
					"""
					value = self.get_where_clause_value(data.get("params", {}).get(p), param, error=True)
				value = [value]
			elif is_copy == "is for copies" and pformat=="pdf":
				#set the number of copies
				#indicate the index of param is for copies
				copies["pram_copy_index"] = len(pram)
				values = utils.get_default_param_value(param, error=False) or ""
				value = self.get_param_values(values)

			elif is_copy == "is for page number" and pformat=="pdf":
				copies["pram_copy_page_index"] = len(pram)

			elif is_copy == "is for server hook":#_("is for server hook"):
				#don't do server hook here. Get first all defaults values
				#if not value:
					#if not data then get default first
				value = utils.get_default_param_value(param, error=False)
				pram_server.append({"name":p, 'value': value, "attrs": param})
				continue
			elif is_copy == "is doctype id":
				values = data.get("params", {}).get(p) or param.jasper_param_value or ""
				if not values or (isinstance(values, basestring) and len(values.split(":")) > 1):
					field_name = values or param.jasper_field_doctype.strip()
					f = field_name.split(":")
					if len(f) > 2:
						doctype = f[0]
						docname = f[1]
						field = f[2]
					elif len(f) > 1:
						doctype = f[0]
						field = f[1]
						docname = data.get('ids', [])[0]
					else:
						doctype = doc.jasper_doctype
						docname = data.get('ids', [])[0]
						field = f[0]
					frappe_doc = frappe.get_doc(doctype, docname)
					values = getattr(frappe_doc, field)

				value = self.get_param_values(values)
				print "value do_params %s" % value

			else:
				#value sent take precedence from value in doctype jasper_param_value
				values = data.get("params", {}).get(p) or param.jasper_param_value or ""
				value = self.get_param_values(values)


			if param.jasper_param_type != "String":
				for idx, val in enumerate(value):
					value[idx] = str(val)
			"""
			if param.jasper_param_type == "Int":
				from jasper_erpnext_report.jasper_reports import Integer
				for idx, val in enumerate(value):
					value[idx] = Integer(val)
			"""

			pram.append({"name":p, 'value':value})

		return (pram, pram_server, copies)

	def get_reports_list_from_db(self, filters_report=None, filters_param=None):
		return utils.jasper_report_names_from_db(origin=self.get_report_origin(), filters_report=filters_report, filters_param=filters_param)

	def get_query_jrxmlFile_from_server(self, file_content):
		query = ""
		xmldoc = JasperXmlReport(BytesIO(file_content))
		list_query = xmldoc.get_query()
		if list_query:
			query = list_query[0].text
		return query

	def check_ids_in_hooks(self, doc, data, params):

		method = "on_jasper_params_ids"
		res = utils.call_hook_for_param(doc, method, data, params)
		"""
		Hook must return a dict with this fields: {"ids": ["name_id1", "name_id2"], "report_type": "List"}
		"""
		if res:
			data['name_ids'] = res.get('ids', [])
			"""
			The hooks method is responsible for change to the appropriate report type: Form or List
			default is Form
			"""
			data['jasper_report_type'] = res.get('report_type', "Form")
		return res

	def get_where_clause_value(self, value, param, error=False):

		if value:
			if isinstance(value, basestring):
				a = ["'%s'" % frappe.utils.strip(t) for t in value.split(",")]
			else:
				a = ["'%s'" % unicode(t) for t in value]
		else:
			"""
			get default value for id
			"""
			value = utils.get_default_param_value(param, error=error)
			if isinstance(value, basestring):
				a = ["'%s'" % frappe.utils.strip(t) for t in value.split(",")]
			elif value is not None:
				a = ["'%s'" % unicode(t) for t in list(value)]
			else:
				"""
				If there is no default value for id then return. Probably there is one in the sended parameters
				The Administrator need to set the parameter type to Ask` ad remove his default values
				"""
				return

		value = "where name %s (%s)" % (param.param_expression, ",".join(a))
		return value

	def update_jasper_reqid_record(self, reqId, data):

		frappe.db.sql("""update tabJasperReqids set data=%s, lastupdate=NOW()
			where reqid=%s""",(str(data['data']), reqId))
		# also add to memcache
		utils.jaspersession_set_value(reqId, data)
		frappe.db.commit()

	def get_jasper_reqid_data(self, reqId):
		print "reqId %s" % reqId
		data = utils.get_jasper_data(reqId, get_from_db=self.get_jasper_reqid_data_from_db, args=[reqId])
		if not data:
			utils.delete_jasper_session(reqId, "tabJasperReqids where reqid='%s'" % reqId)
		return frappe._dict({'data': data})

	def get_jasper_reqid_data_from_db(self, *reqId):
		#pos 0  must be request id
		rec = frappe.db.sql("""select reqid, data
			from tabJasperReqids where
			TIMEDIFF(NOW(), lastupdate) < TIME(%s) and reqid=%s""", (utils.get_expiry_period(reqId[0]),reqId[0]))
		return rec

	def insert_jasper_reqid_record(self, reqId, data):
			frappe.db.sql("""insert into tabJasperReqids
				(reqid, data, lastupdate)
				values (%s , %s, NOW())""",
					(reqId, str(data['data'])))
			# also add to memcache
			utils.jaspersession_set_value(reqId, data)
			frappe.db.commit()

	def get_session_from_db(self, tab="tabJasperClientHtmlDocs"):
		rec = frappe.db.sql("""select name, data
			from {0}""".format(tab))
		return rec

	def prepare_report_async(self, path, doc, data=None, params=None, pformat="pdf", ncopies=1, for_all_sites=0):
		resps = []
		frappe.local.fds = None
		frappe.local.batch = None
		data = self.run_report_async(doc, data=data, params=params)
		"""
		Run one report at a time for Form type report and many ids
		"""
		if (doc.jasper_report_type == "Form" or data.get('jasper_report_type', None) == "Form") and not data.get("is_doctype_id", None):
			ids = data.get('ids', [])[:]
			for id in ids:
				data['ids'] = [id]
				resps.append(self._run_report_async(path, doc, data=data, params=params, pformat=pformat, ncopies=ncopies, for_all_sites=for_all_sites))
		else:
			resps.append(self._run_report_async(path, doc, data=data, params=params, pformat=pformat, ncopies=ncopies, for_all_sites=for_all_sites))

		if self.report_origin == "local":
			resps = resps[:1]
			cresp = self.prepareCollectResponse(resps)
			cresp["origin"] = "local"
			cresp["pformat"] = pformat
			self.frappe_task.setResult([cresp])
			frappe.local.batch.batchReport.export()
			if frappe.local.batch.outtype == 7:#html file
				content = get_file(frappe.local.batch.outputPath + os.sep + frappe.local.batch.reportName + ".html")
				self.copy_images(content, frappe.local.batch.outputPath + os.sep, frappe.local.batch.reportName, data.get("report_name"), frappe.local.site)
		else:
			cresp = self.prepareCollectResponse(resps)
			cresp["origin"] = "server"
			cresp["pformat"] = pformat
			#self.frappe_task.setResult([cresp])
			#self.frappe_task.setReadyTask()
			from frappe.async import emit_via_redis
			task_id = "Local-" + frappe.local.task_id
			response = {}
			response.update({
				"status": "Success",
				"task_id": task_id,
				"result": [cresp]
			})
			emit_via_redis("task_status_change", response, frappe.local.site + ":task_progress:" + task_id)

		return cresp

	#Override by descendents: JasperServer and JasperLocal
	def _run_report_async(self, path, doc, data=None, params=None, pformat="pdf", ncopies=1, for_all_sites=0):
		pass

	def prepareResponse(self, detail, reqId):
		uri = detail.get("reportURI", None)
		res = {"requestId": reqId, "uri": uri, "reqtime": frappe.utils.now()}
		if detail.get("status", "not ready") == "ready":
			ids = []
			for i in detail.get("exports"):
				if i.get("status") == "ready":
					id = i.get("id")
					outr = i.get("outputResource", {})
					contentType = outr.get("contentType", "")
					if "html" in contentType:
						options = i.get("options", {})
						attachs = i.get("attachments", {})
						fileName = outr.get("fileName", None)
						if not fileName:
							import re
							fname = uri.rsplit("/",1)[1]
							fname = re.sub('\t|\s', '', fname)
							fileName = fname + ".html"
						ids.append({"id":id, "fileName": fileName, "attachmentsPrefix": options.get("attachmentsPrefix"),
									"baseUrl": options.get("baseUrl"), "attachments": attachs, "contentType": contentType})
					else:
						ids.append({"id":id, "fileName": outr.get("fileName"), "contentType": contentType})
				else:
					res['status'] = "not ready"
					del ids[:]
					break
			res["ids"] = ids
		return res

	def prepareCollectResponse(self, resps):
		reqids = []
		status = "ready"
		report_name = resps[0][0].get("report_name")
		for resp in reversed(resps):
			ncopies = []
			for r in resp:
				requestId = r.get('requestId')
				ncopies.append(requestId)
				if r.get('status') == "ready":
					continue
				status = "not ready"
			reqids.append(ncopies)
		res = self.make_internal_reqId(reqids, status, report_name)

		return res

	def make_internal_reqId(self, reqids, status, report_name):
		intern_reqId = "intern_reqid_" + uuid.uuid4().hex
		reqtime = frappe.utils.now()
		reqDbObj = {"data":{"reqids": reqids, "report_name": report_name, "last_updated": reqtime,'session_expiry': utils.get_expiry_period(intern_reqId), "db": frappe.conf.db_name, "site": frappe.local.site}}
		self.insert_jasper_reqid_record(intern_reqId, reqDbObj)
		res = {"requestId": intern_reqId, "reqtime": reqtime, "status": status}
		return res

	def run_report_async(self, doc, data=None, params=None):
		data = data or {}

		if doc.jasper_report_type == "Server Hooks":
			self.check_ids_in_hooks(doc, data, params)

		#if it is a report no need for ids
		if data.get("fortype", None) == "query-report":
			return data

		if not doc.jasper_report_type == "General":

			name_ids = data.get('name_ids', [])
			if not name_ids:
				res = None
				if doc.jasper_report_type != "Server Hooks":
					res = self.check_ids_in_hooks(doc, data, params)
				if not res:
					frappe.throw(_("Report {} input parameters error. This report is of type {} and needs at least one name.".format(doc.get('name'),doc.jasper_report_type)))
					return
		#In General type you may change to Form or List and give ids and change some initial data
		if data.get('jasper_report_type', None) == "Form" or doc.jasper_report_type == "Form":
			if not data.get('ids', None):
				data['ids'] = []
			for elem in data.get('name_ids', []):
				data['ids'].append(elem)

		elif data.get('jasper_report_type', None) == "List" or doc.jasper_report_type == "List":
			data['ids'] = data.get('name_ids', [])

		return data

	def polling(self, reqId):
		pass

	def report_polling_base(self, reqId, report_name):
		result = []
		req = [{}]
		error = None
		data = self.get_jasper_reqid_data(reqId)
		if data:
			d = data['data']
			for ids in d.get('reqids'):
				for id in ids:
					res = self.polling(id)
					if not res:
						frappe.msgprint(_("There was an error in report request."),raise_exception=True)
					if res.get('status', "not ready") != "ready":
						result = []
						error = res.get("error", None)
						break
					result.append(res)
				if not result:
					break
			for r in result:
				new_data = {"data":{"result": r, "report_name": report_name, "last_updated": frappe.utils.now(), 'session_expiry': d.get('session_expiry')}}
				self.update_jasper_reqid_record(r.get('requestId'), new_data)
			if result:
				req = [{"requestId": reqId, "reqtime": frappe.utils.now(), "status": "ready"}]
		else:
			frappe.throw(_("Report Not Found."))
		if error:
			req[0]["error"] = error
		return req

	def get_html_path(self, report_name, localsite=None, content=None):
		import hashlib
		site = localsite or frappe.local.site
		if not self.html_hash:
			hash_obj = hashlib.md5(frappe.utils.encode(content))
			self.html_hash = hash_obj.hexdigest()
		self.report_html_path = get_html_reports_path(report_name, localsite=site, hash=self.html_hash)
		return self.report_html_path

	def save_html_cache(self, report_name, reportPath):
		name = "client_html_" + report_name.replace(" ", "_")
		new_data = frappe._dict({'data': {}})
		data = utils.get_jasper_data(name, get_from_db=self.get_session_from_db, tab="tabJasperClientHtmlDocs")
		if data:
			rp = data['data']['reportPath']
			if rp == reportPath:
				data['data']['hash'] = self.html_hash
				utils.update_list_all_memcache_db(data, cachename=name)
				return
		new_data['data']['reportPath'] = reportPath
		new_data['data']['hash'] = self.html_hash
		utils.insert_list_all_memcache_db(new_data['data'], cachename=name)

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

	#check what docs to show when global
	def filter_perm_roles(self, data):
		removed = 0
		count = 0
		toremove = []
		for k,v in data.iteritems():
			if isinstance(v, dict):
				count += 1
				perms = v.pop("perms", None)
				frappe.flags.mute_messages = True
				found = utils.check_frappe_permission("Jasper Reports", k, ptypes=("read", ))
				frappe.flags.mute_messages = False
				if not found:
					toremove.append(k)
					removed = removed + 1
		for k in toremove:
			data.pop(k, None)
		data['size'] = count - removed

	#check what docs to show when inside doctype
	def doc_filter_perm_roles(self, doctype, data, docnames):
		new_data = {}
		added = 0
		for k,v in data.iteritems():
			if isinstance(v, dict):
				if v.get("Doctype name") == doctype or v.get("report") == doctype:
					if docnames and v.get('jasper_report_type') == "List":
						continue
					if frappe.local.session['user'] != "Administrator":
						frappe.flags.mute_messages = True
						to_remove = False
						ptypes = ("read", )
						if not utils.check_frappe_permission("Jasper Reports", k, ptypes=ptypes):
							continue
						for docname in docnames:
							if not utils.check_frappe_permission(doctype, docname, ptypes=ptypes):
								to_remove = True
								break
						frappe.flags.mute_messages = False
						if to_remove == True:
							continue
					new_data[k] = v
					added = added + 1
		new_data['size'] = added
		return new_data

	#check if exist at least one docname in data
	def check_docname(self, data, doctype, report):
		ret = False
		if not data:
			return ret
		for k,v in data.iteritems():
			if isinstance(v, dict):
				if v.get("Doctype name") == doctype or v.get("report") == report:
					ret = True
					break
		return ret

	def validate_ticket(self, data):
		last_timeout = utils.jaspersession_get_value("last_jasper_session_timeout")
		request_time = data.get("reqtime")
		time_diff = frappe.utils.time_diff_in_seconds(request_time, last_timeout) if last_timeout else None
		if time_diff and time_diff < 0:
			frappe.throw(_("RequestID not Valid."))

	def make_pdf(self, fileName, content, pformat, merge_all=True, pages=None):
		return None

	def send_email(self, body, subject, user="no_reply@gmail.com"):
		from jasper_erpnext_report.utils.utils import getFrappeVersion
		version = getFrappeVersion().major
		if version < 5:
			import frappe.utils.email_lib
			try:
				frappe.utils.email_lib.sendmail_to_system_managers(subject, body)
			except Exception as e:
				_logger.info(_("Jasper Server, email error: {}").format(e))
				_logger.error(_("Jasper Server, email error: {}").format(e))
		else:
			import frappe.email
			try:
				frappe.email.sendmail_to_system_managers(subject, body)
			except Exception as e:
				_logger.info(_("Jasper Server, email error: {}").format(e))
				_logger.error(_("Jasper Server, email error: {}").format(e))




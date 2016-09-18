__author__ = 'luissaguas'


#import json
from jnius import PythonJavaClass, java_method
import frappe, re, os


class FrappeTask(PythonJavaClass):
	__javainterfaces__ = ['IFrappeTask']

	def read_config(self):
		config = frappe.get_conf() or {}
		curr_site = os.path.join("currentsite.txt")
		config.default_site = frappe.read_file(curr_site) or frappe.local.site

		return config

	def conf(self):
		conf = self.read_config()
		return conf

	def __init__(self, task_id, result):
		super(FrappeTask, self).__init__()
		self.task_id = "Local-" + task_id
		self.result = result

	def get_hostname(self, url):
		if (not url): return None;
		if (url.find("://") > -1):
			url = url.split('/')[2]
		return url[0:url.find(":")] if (re.search(":", url)) else url

	def get_site_name(self):
		if (frappe.get_request_header('x-frappe-site-name')):
			return self.get_hostname(frappe.get_request_header('x-frappe-site-name'))

		conf = self.conf()
		if (frappe.get_request_header('host') in ['localhost', '127.0.0.1'] and conf.default_site):
			return conf.default_site

		if (frappe.get_request_header('origin')):
			return self.get_hostname(frappe.get_request_header('origin'))

		return self.get_hostname(frappe.get_request_header('host'))

	def setResult(self, result):
		self.result = result

	def emit_via_redis(self):
		from frappe.async import emit_via_redis
		import frappe

		response = {}
		response.update({
			"status": "Success",
			"task_id": self.task_id,
			"result": self.result
		})
		sitename = self.get_site_name() or frappe.local.site
		emit_via_redis("task_status_change", response, sitename + ":task_progress:" + self.task_id)

	@java_method('()V')
	def setReadyTask(self):
		self.emit_via_redis()


"""

redis_server = None

def get_redis_server():
	global redis_server
	if not redis_server:
		from redis import Redis
		redis_server = Redis.from_url(conf.get("async_redis_server") or "redis://localhost:12311")
	return redis_server


def emit_via_redis(event, message, room):

	r = get_redis_server()

	try:
		r.publish('events', frappe.as_json({'event': event, 'message': message, 'room': room}))
	except redis.exceptions.ConnectionError:
		# print frappe.get_traceback()
		pass



"""
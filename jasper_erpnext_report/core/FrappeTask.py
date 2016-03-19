__author__ = 'luissaguas'


#import json
from jnius import PythonJavaClass, java_method


class FrappeTask(PythonJavaClass):
	__javainterfaces__ = ['IFrappeTask']

	def __init__(self, task_id, result):
		super(FrappeTask, self).__init__()
		self.task_id = "Local-" + task_id
		self.result = result

	def setResult(self, result):
		self.result = result

	@java_method('()V')
	def setReadyTask(self):
		from frappe.async import emit_via_redis
		import frappe

		response = {}
		response.update({
			"status": "Success",
			"task_id": self.task_id,
			"result": self.result
		})
		emit_via_redis("task_status_change", response, frappe.local.site + ":task_progress:" + self.task_id)


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
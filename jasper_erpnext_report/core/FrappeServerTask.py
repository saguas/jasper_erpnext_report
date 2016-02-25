


class FrappeTask(object):

	def __init__(self, task_id, result):
		self.task_id = "Local-" + task_id
		self.result = result

	def setResult(self, result):
		self.result = result

	def setReadyTask(self):
		from frappe.async import emit_via_redis

		response = {}
		response.update({
			"status": "Success",
			"task_id": self.task_id,
			"result": self.result
		})
		emit_via_redis("task_status_change", response, "task:" + self.task_id)
		
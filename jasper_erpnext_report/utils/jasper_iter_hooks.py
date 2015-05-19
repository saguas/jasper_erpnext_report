from __future__ import unicode_literals
__author__ = 'luissaguas'

import frappe
from frappe import _

"""

HOOKS:
		jasper_after_sendmail(data, url, file_name, file_path); jasper_before_sendmail(data, file_name, output, url, **kargs);
		jasper_after_get_report(file_name, file_output, url, filepath); jasper_before_get_report(data);
		jasper_after_list_for_doctype(doctype, docnames, report, lista); jasper_before_list_for_doctype(doctype, docnames, report);
		jasper_after_list_for_all(lista); jasper_before_list_for_all();
"""

class JasperHooks:
	def __init__(self, hook_name, docname=None, fallback=None):
		self.hook_name = hook_name
		self.current = 0
		self.methods = frappe.get_hooks().get(self.hook_name) or (fallback if fallback is not None else [])
		if isinstance(self.methods, dict):
			if docname in self.methods.keys():
				self.methods = self.methods[docname]
			else:
				self.methods = fallback if fallback is not None else []
		self.methods_len = len(self.methods)


	def __iter__(self):
		return self

	def next(self):
		if self.current >= self.methods_len:
			raise StopIteration
		else:
			return self.get_next_jasper_hook_method()

	def get_next_jasper_hook_method(self):
		curr_method = frappe.get_attr(self.methods[self.current])
		self.current += 1
		return curr_method


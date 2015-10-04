import jasper_erpnext_report.jasper_reports as jr
import frappe
from frappe import _

def jasper_compile(jrxml, destFileName):
	try:
		compiler = jr.ReportCompiler()
		compiler.compile(jrxml,destFileName)
	except Exception as e:
		import jasper_erpnext_report as jer
		if jer.pyjnius == False:
			frappe.throw(_("Please install pyjnius python module."))
			return
		frappe.throw(_("Error while compiling report %s, error is: %s." % (jrxml, e)))
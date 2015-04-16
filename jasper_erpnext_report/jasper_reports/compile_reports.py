import jasper_erpnext_report.jasper_reports as jr
import logging, frappe
from frappe import _

_logger = logging.getLogger(frappe.__name__)

def jasper_compile(jrxml, destFileName):
	_logger.info("jasper_compile jrxml dir {0} destFileName {1}".format(jrxml, destFileName))
	try:
		compiler = jr.ReportCompiler()
		compiler.compile(jrxml,destFileName)
	except Exception as e:
		if jr.pyjnius == False:
			frappe.throw(_("Please install pyjnius python module."))
			return
		frappe.throw(_("Error while compiling report %s, error is: %s." % (jrxml, e)))
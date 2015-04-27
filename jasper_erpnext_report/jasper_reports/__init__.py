import os, frappe
import jasper_erpnext_report as jr

_logger = frappe.get_logger(__name__)

try:
	import jnius_config as jc
	jr.pyjnius = True

	if not jc.vm_running:
		jc.add_options('-Djava.awt.headless=true')
	else:
		_logger.info("vm_running: {}".format(jc.vm_running))
except:
	print "jnius_config not found"
	jr.pyjnius = False

norm_path = os.path.normpath
join_path = os.path.join
dirname = os.path.dirname
parent_path = dirname(dirname(__file__))
rel_path = os.path.relpath(os.path.join(parent_path, "java"),dirname(__file__))
rel_path_curr = os.path.relpath(parent_path, os.getcwd())
try:
	os.environ['CLASSPATH'] = os.environ.get('CLASSPATH',"") + ":" +norm_path(join_path(parent_path,"java/lib/*")) + ":."
except:
	print "Error in setting java classpath."

try:
	from jnius import autoclass

	def getJavaClass(jclass):
		return autoclass(jclass)

	HashMap = getJavaClass('java.util.HashMap')
	String = getJavaClass('java.lang.String')
	Integer = getJavaClass('java.lang.Integer')
	ArrayList = getJavaClass('java.util.ArrayList')

	ReportCompiler = getJavaClass('ReportCompiler')

	ExportReport = getJavaClass('ExportReport')
	jr.pyjnius = True
	print "pyjnius is ok: {}".format(jr.pyjnius)
except Exception, e:
	print "pyjnius is not ok: {}".format(e)
	jr.pyjnius = False
#from __future__ import unicode_literals
import os, logging, frappe
import jasper_erpnext_report as jr

_logger = logging.getLogger(frappe.__name__)

try:
	import jnius_config as jc
	jr.pyjnius = True
#print "getclasspath {}".format(jc.get_options())
#jc.add_options('-Xrs', '-Xmx4096')

	if not jc.vm_running:
		jc.add_options('-Djava.awt.headless=true')
	#	pass
	else:
		_logger.info("jasper_reports __init__ vm_running {}".format(jc.vm_running))
except:
	jr.pyjnius = False
#jc.set_classpath('/Users/saguas/erpnext4/erpnext/erpnext_mac/jasperreports-5.6.1/lib/*:.')#,'/Users/luissaguas/erpnext4/erpnext/erpnext/erpnext_mac/jasperreports-5.6.1/dist/jasperreports-5.6.1.jar','/Library/Java/JavaVirtualMachines/jdk1.7.0_51.jdk/Contents/Home/jre/lib/*','/Library/Java/JavaVirtualMachines/jdk1.7.0_51.jdk/Contents/Home/lib/*','/Users/luissaguas/openerp-7-ultimo/myaddons/addons/jasper_reports/java/lib/*')
#os.environ['CLASSPATH'] = "/Users/saguas/erpnext4/erpnext/erpnext_mac/jasperreports-5.6.1/lib/*:."
#os.environ['CLASSPATH'] = "../../../../java/lib/*" + ":../java/*:."
#rel_path = os.path.relpath("../", os.path.dirname(__file__))
norm_path = os.path.normpath
join_path = os.path.join
dirname = os.path.dirname
parent_path = dirname(dirname(__file__))
rel_path = os.path.relpath(os.path.join(parent_path, "java"),dirname(__file__))
rel_path_curr = os.path.relpath(parent_path, os.getcwd())
#os.environ['CLASSPATH'] = os.path.join(parent_path, "java/lib/*") + ":" + os.path.join(parent_path, "java/*") 
#os.environ['CLASSPATH'] = norm_path(os.path.join(rel_path, "lib/*")) + ":" + os.path.join(rel_path, "*") 

#os.environ['CLASSPATH'] = norm_path(join_path(parent_path,"java/*.class")) + ":" + norm_path(join_path(parent_path,"java/lib/*")) + ":."
os.environ['CLASSPATH'] = os.environ['CLASSPATH'] + ":" +norm_path(join_path(parent_path,"java/lib/*")) + ":."
#jc.expand_classpath()
print 'py CLASSPATH: ', os.environ['CLASSPATH']
#os.getcwd()
_logger.info("jasper_reports __init__ new CLASSPATH {0} curr dir {1}".format(os.environ['CLASSPATH'],rel_path_curr))

try:
	from jnius import autoclass

	def getJavaClass(jclass):
		return autoclass(jclass)

	DefaultTableModel = getJavaClass('javax.swing.table.DefaultTableModel')
	String = getJavaClass('java.lang.String')
	ArrayList = getJavaClass('java.util.ArrayList')
#JRException = getJavaClass('net.sf.jasperreports.engine.JRException')
#JREmptyDataSource = getJavaClass('net.sf.jasperreports.engine.JREmptyDataSource')
#JasperFillManager = getJavaClass('net.sf.jasperreports.engine.JasperFillManager')
	HashMap = getJavaClass('java.util.HashMap')

	ReportCompiler = getJavaClass('ReportCompiler')
#teste = ReportCompiler()
#print "will compile my teste!!! {}".format(os.environ['CLASSPATH'])
#teste.compile("/Users/saguas/erpnext4/erpnext/erpnext_mac/frappe-bench/apps/jasper_erpnext_report/jasper_erpnext_report/java/Cherry.jrxml",\
#			"/Users/saguas/erpnext4/erpnext/erpnext_mac/frappe-bench/apps/jasper_erpnext_report/jasper_erpnext_report/java/Cherry.jasper")
#teste.compile(str("Cherry.jrxml"),str("Cherry.jasper"))
	ExportReport = getJavaClass('ExportReport')
	ExportQueryReport = getJavaClass('ExportQueryReport')
	jr.pyjnius = True
	print "pyjnius is ok 3: {}".format(jr.pyjnius)
except:
	jr.pyjnius = False
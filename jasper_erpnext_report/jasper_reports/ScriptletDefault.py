__author__ = 'saguas'

import frappe
from jnius import PythonJavaClass
from jnius.jnius import java_method

class JasperCustomScripletDefault(object):
	""" Jasperreports Scriptlet
	Methods to call in JasperScriplet Object bellow:
		java.lang.Object	getFieldValue(java.lang.String fieldName)
		java.lang.Object	getParameterValue(java.lang.String parameterName)
		java.lang.Object	getParameterValue(java.lang.String parameterName, boolean mustBeDeclared)
		java.lang.Object	getVariableValue(java.lang.String variableName)
		void	setData(java.util.Map<java.lang.String,JRFillParameter> parsm, java.util.Map<java.lang.String,JRFillField> fldsm, java.util.Map<java.lang.String,JRFillVariable> varsm, JRFillGroup[] grps)
		void	setVariableValue(java.lang.String variableName, java.lang.Object value)
	"""
	def __init__(self, JasperScriplet, ids=None, data=None, cols=None, doctype=None, docname=None):
		if isinstance(ids, basestring):
			ids = [ids]

		self.JS = JasperScriplet
		self.ids = ids or []
		self.doctype = doctype
		self.docname = docname
		self.data = data
		self.cols = cols

	def beforeReportInit(self):
		print "beforeReportInit"
		return

	def afterReportInit(self):
		print "afterReportInit"
		return

	def beforePageInit(self):
		print "beforePageInit"
		return

	def afterPageInit(self):
		print "afterPageInit"
		return

	def beforeColumnInit(self):
		print "beforeColumnInit"
		return

	def afterColumnInit(self):
		print "afterColumnInit"
		return

	def beforeGroupInit(self, gname):
		print "beforeGroupInit name: {}".format(gname)
		return

	def afterGroupInit(self, gname):
		print "afterGroupInit name: {}".format(gname)
		return

	def beforeDetailEval(self):
		print "beforeDetailEval"
		return

	def afterDetailEval(self):
		print "afterDetailEval"
		return

class _JasperCustomScriptlet(PythonJavaClass):
	__javainterfaces__ = ['IFrappeScriptlet']

	def __init__(self, JasperScriplet, scl):
		super(_JasperCustomScriptlet, self).__init__()
		"""This field is the scriptlet passed in hook jasper_scriptlet """
		self.Sl = scl
		"""this field give us access to JavaFrappeScriptlet Object.
			With it we can call implemented fields of JRAbstractScriptlet such as:
				java.lang.Object	getFieldValue(java.lang.String fieldName)
				java.lang.Object	getParameterValue(java.lang.String parameterName)
				java.lang.Object	getParameterValue(java.lang.String parameterName, boolean mustBeDeclared)
				java.lang.Object	getVariableValue(java.lang.String variableName)
				void	setData(java.util.Map<java.lang.String,JRFillParameter> parsm, java.util.Map<java.lang.String,JRFillField> fldsm, java.util.Map<java.lang.String,JRFillVariable> varsm, JRFillGroup[] grps)
				void	setVariableValue(java.lang.String variableName, java.lang.Object value)
		"""
		self.JS = JasperScriplet

	@java_method('()V')
	def beforeReportInit(self):
		self.Sl.beforeReportInit()
		return

	@java_method('()V')
	def afterReportInit(self):
		self.Sl.afterReportInit()
		return

	@java_method('()V')
	def beforePageInit(self):
		self.Sl.beforePageInit()
		return

	@java_method('()V')
	def afterPageInit(self):
		self.Sl.afterPageInit()
		return

	@java_method('()V')
	def beforeColumnInit(self):
		self.Sl.beforeColumnInit()
		return

	@java_method('()V')
	def afterColumnInit(self):
		self.Sl.afterColumnInit()
		return

	@java_method('(Ljava/lang/String;)V')
	def beforeGroupInit(self, gname):
		self.Sl.beforeGroupInit(gname)
		return

	@java_method('(Ljava/lang/String;)V')
	def afterGroupInit(self, gname):
		self.Sl.afterGrouptInit(gname)
		return

	@java_method('()V')
	def beforeDetailEval(self):
		self.Sl.beforeDetailEval()
		return

	@java_method('()V')
	def afterDetailEval(self):
		self.Sl.afterDetailEval()
		return

	@java_method('(Ljava/lang/String;[Ljava/lang/Object;)Ljava/lang/Object;')
	def callPythonMethod(self, methodName, args):
		method = getattr(self.Sl, methodName)
		return method(args)
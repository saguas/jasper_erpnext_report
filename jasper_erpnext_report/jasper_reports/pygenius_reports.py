import jasper_erpnext_report.jasper_reports as jr

#JREmptyDataSource = autoclass('net.sf.jasperreports.engine.JREmptyDataSource')
#JRException = autoclass('net.sf.jasperreports.engine.JRException')
#JasperFillManager = autoclass('net.sf.jasperreports.engine.JasperFillManager')
#HashMap = autoclass('java.util.HashMap')

jr.JasperFillManager.fillReportToFile("first_report.jasper", jr.HashMap(), jr.JREmptyDataSource())

#PdfExportDemo = autoclass('PdfExportDemo')

#RestClientConfiguration = jnius.autoclass('com.jaspersoft.jasperserver.jaxrs.client.core.RestClientConfiguration')
#JasperserverRestClient = jnius.autoclass('com.jaspersoft.jasperserver.jaxrs.client.core.JasperserverRestClient')

#config =  RestClientConfiguration(r"http://localhost:80817jasperserver")
#client = JasperserverRestClient(config)

#session = client.authenticate("jasperadmin", "jasperadmin")

#print "client {0}".format(client)
pdf = jr.PdfExportDemo()

print "pdf {}".format(dir(jr.PdfExportDemo))

pdf.pdfExport('FirstReport')

Stack = jr.getJavaClass('java.util.Stack')
stack = Stack()
stack.push('hello')
stack.push('world')
print stack.pop() # --> 'world'
print stack.pop() # --> 'hello'

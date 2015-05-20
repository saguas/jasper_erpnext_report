import net.sf.jasperreports.engine.JRException;
import net.sf.jasperreports.engine.export.oasis.JROdsExporter;
import net.sf.jasperreports.engine.export.oasis.JROdtExporter;
import net.sf.jasperreports.engine.export.ooxml.JRDocxExporter;
import net.sf.jasperreports.engine.export.ooxml.JRPptxExporter;
import net.sf.jasperreports.engine.export.ooxml.JRXlsxExporter;
import net.sf.jasperreports.engine.export.JRXhtmlExporter;
import net.sf.jasperreports.engine.export.JRPdfExporter;
import net.sf.jasperreports.engine.export.JRRtfExporter;
import net.sf.jasperreports.engine.export.JRXlsExporter;
import net.sf.jasperreports.export.SimpleExporterInput;
import net.sf.jasperreports.export.SimpleOutputStreamExporterOutput;
import net.sf.jasperreports.export.SimpleHtmlExporterOutput;
import net.sf.jasperreports.export.SimpleWriterExporterOutput;
import net.sf.jasperreports.engine.JasperPrint;

import net.sf.jasperreports.export.SimpleXlsxReportConfiguration;
import net.sf.jasperreports.export.SimpleXlsReportConfiguration;
import net.sf.jasperreports.export.SimpleOdsReportConfiguration;
import net.sf.jasperreports.engine.export.JRHtmlExporterParameter;
import net.sf.jasperreports.engine.JRExporterParameter;
import net.sf.jasperreports.web.util.WebHtmlResourceHandler;
import net.sf.jasperreports.engine.export.FileHtmlResourceHandler;

import java.util.List;
import java.io.File;

public class MakeReport
{
	
	private List<JasperPrint> jasperPrintList;
	
	private String[] extension = {".docx",".ods",".odt", ".rtf", ".xls", ".xlsx", ".pptx", ".html", ".pdf"};
	
	public MakeReport(List<JasperPrint> jasperPrintList){
		this.jasperPrintList = jasperPrintList;
	}

	public void makeReport(int type, String outputPathName, String fileName){
  
	  try{
		  switch(type){
		      case 0:
		          JRDocxExporter docxexporter = new JRDocxExporter();
		          //docxexporter.setParameter(JRExporterParameter.JASPER_PRINT, this.jasperPrint);
				  docxexporter.setExporterInput(SimpleExporterInput.getInstance(this.jasperPrintList));
				  docxexporter.setExporterOutput(new SimpleOutputStreamExporterOutput(outputPathName + extension[type]));
		          //docxexporter.setParameter(JRExporterParameter.OUTPUT_FILE_NAME, this.outputPathName + ".docx");
		          docxexporter.exportReport();
		          break;
		      case 1:
		          JROdsExporter odsexporter = new JROdsExporter();
		          //odsexporter.setParameter(JRExporterParameter.JASPER_PRINT, this.jasperPrint);
				  odsexporter.setExporterInput(SimpleExporterInput.getInstance(this.jasperPrintList));
				  odsexporter.setExporterOutput(new SimpleOutputStreamExporterOutput(outputPathName + extension[type]));
		          //odsexporter.setParameter(JRExporterParameter.OUTPUT_FILE_NAME, this.outputPathName + ".ods");	
				  SimpleOdsReportConfiguration odsconfig = new SimpleOdsReportConfiguration();
				  odsconfig.setOnePagePerSheet(false);
				  odsexporter.setConfiguration(odsconfig);
		          //odsexporter.setParameter(JRXlsExporterParameter.IS_ONE_PAGE_PER_SHEET, Boolean.TRUE);
		          odsexporter.exportReport();
		          break; 
		      case 2:
		          JROdtExporter odtexporter = new JROdtExporter();
		          //odtexporter.setParameter(JRExporterParameter.JASPER_PRINT, this.jasperPrint);
				  odtexporter.setExporterInput(SimpleExporterInput.getInstance(this.jasperPrintList));
				  odtexporter.setExporterOutput(new SimpleOutputStreamExporterOutput(outputPathName + extension[type]));
		          //odtexporter.setParameter(JRExporterParameter.OUTPUT_FILE_NAME, this.outputPathName + ".odt");
		          odtexporter.exportReport();
		          break;
		      case 3:
		          JRRtfExporter rtfexporter = new JRRtfExporter();
				  rtfexporter.setExporterInput(SimpleExporterInput.getInstance(this.jasperPrintList));
				  rtfexporter.setExporterOutput(new SimpleWriterExporterOutput(outputPathName + extension[type]));
		          //rtfexporter.setParameter(JRExporterParameter.JASPER_PRINT, this.jasperPrint);
		          //rtfexporter.setParameter(JRExporterParameter.OUTPUT_FILE_NAME, this.outputPathName + ".rtf");
		          rtfexporter.exportReport();
		          break;
		      case 4:
		          JRXlsExporter xlsexporter = new JRXlsExporter();
				  xlsexporter.setExporterInput(SimpleExporterInput.getInstance(this.jasperPrintList));
				  xlsexporter.setExporterOutput(new SimpleOutputStreamExporterOutput(outputPathName + extension[type]));
		          //xlsexporter.setParameter(JRExporterParameter.JASPER_PRINT, this.jasperPrint);
		          //xlsexporter.setParameter(JRExporterParameter.OUTPUT_FILE_NAME, this.outputPathName + ".xls");
				  SimpleXlsReportConfiguration xlsconfig = new SimpleXlsReportConfiguration();
				  xlsconfig.setOnePagePerSheet(false);
				  xlsexporter.setConfiguration(xlsconfig);
		          //xlsexporter.setParameter(JRXlsExporterParameter.IS_ONE_PAGE_PER_SHEET, Boolean.TRUE);
		          xlsexporter.exportReport();
		          break;
		      case 5:
		          JRXlsxExporter xlsxexporter = new JRXlsxExporter();
				  xlsxexporter.setExporterInput(SimpleExporterInput.getInstance(this.jasperPrintList));
				  xlsxexporter.setExporterOutput(new SimpleOutputStreamExporterOutput(outputPathName + extension[type]));
		          //xlsxexporter.setParameter(JRExporterParameter.JASPER_PRINT, this.jasperPrint);
		          //xlsxexporter.setParameter(JRExporterParameter.OUTPUT_FILE_NAME, this.outputPathName + ".xlsx");
				  SimpleXlsxReportConfiguration xlsxconfig = new SimpleXlsxReportConfiguration();
				  xlsxconfig.setOnePagePerSheet(false);
				  xlsxexporter.setConfiguration(xlsxconfig);
		          //xlsxexporter.setParameter(JRXlsExporterParameter.IS_ONE_PAGE_PER_SHEET, Boolean.TRUE);
		          xlsxexporter.exportReport();
		          break;
		      /*case "jxl":
		          JRExcelApiExporter exporter = new JRExcelApiExporter();
		          exporter.setParameter(JRExporterParameter.OUTPUT_FILE_NAME, reportName + ".rtf");
		          exporter.setParameter(JRXlsExporterParameter.IS_ONE_PAGE_PER_SHEET, Boolean.TRUE);
		          break;*/
		      case 6:
		          JRPptxExporter pptxexporter = new JRPptxExporter();
				  pptxexporter.setExporterInput(SimpleExporterInput.getInstance(this.jasperPrintList));
				  pptxexporter.setExporterOutput(new SimpleOutputStreamExporterOutput(outputPathName + extension[type]));
		          //pptxexporter.setParameter(JRExporterParameter.JASPER_PRINT, this.jasperPrint);
		          //pptxexporter.setParameter(JRExporterParameter.OUTPUT_FILE_NAME, this.outputPathName + ".pptx");
		          pptxexporter.exportReport();
		          break;
		      case 7:
			  	  SimpleHtmlExporterOutput exporterOutput;
		          JRXhtmlExporter xhtmlexporter = new JRXhtmlExporter();
				  xhtmlexporter.setExporterInput(SimpleExporterInput.getInstance(this.jasperPrintList));
				  exporterOutput = new SimpleHtmlExporterOutput(outputPathName + extension[type]);
				  //exporterOutput.setImageHandler(new WebHtmlResourceHandler(fileName + ".html_files/{0}"));
				  //exporterOutput.setImageHandler(new WebHtmlResourceHandler("image?image={0}"));
				  //exporterOutput.setResourceHandler(new FileHtmlResourceHandler(new File("./"), "./images/"));
				  xhtmlexporter.setExporterOutput(exporterOutput);
		          //xhtmlexporter.setParameter(JRExporterParameter.JASPER_PRINT, this.jasperPrintList);
		          //xhtmlexporter.setParameter(JRExporterParameter.OUTPUT_FILE_NAME, outputPathName + ".html");
		          //xhtmlexporter.setParameter(JRHtmlExporterParameter.IS_OUTPUT_IMAGES_TO_DIR, Boolean.TRUE);
		          //xhtmlexporter.setParameter(JRHtmlExporterParameter.IMAGES_URI, "./");
		          //xhtmlexporter.setParameter(JRHtmlExporterParameter.IMAGES_DIR_NAME, "./images/");
		          xhtmlexporter.exportReport();
		          break;
		      case 8:
		      default:
		          JRPdfExporter pdfexporter = new JRPdfExporter();
		          //pdfexporter.setParameter(JRExporterParameter.JASPER_PRINT, this.jasperPrint);
				  pdfexporter.setExporterInput(SimpleExporterInput.getInstance(this.jasperPrintList));
				  pdfexporter.setExporterOutput(new SimpleOutputStreamExporterOutput(outputPathName + extension[type]));
		          //pdfexporter.setParameter(JRExporterParameter.OUTPUT_FILE_NAME, this.outputPathName + ".pdf");
		          pdfexporter.exportReport();
		          break;
		  }
	  }
	  catch (JRException e)
	  {
	    e.printStackTrace();
	  }
	
	}
}
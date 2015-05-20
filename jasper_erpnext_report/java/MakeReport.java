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
import net.sf.jasperreports.engine.JasperPrint;

import java.util.List;

public class MakeReport
{
	
	private List<JasperPrint> jasperPrintList;
	
	public MakeReport(List<JasperPrint> jasperPrintList){
		this.jasperPrintList = jasperPrintList;
	}

	public void makeReport(int type, String outputPathName){
  
	  try{
		  switch(type){
		      case 0:
		          JRDocxExporter docxexporter = new JRDocxExporter();
		          //docxexporter.setParameter(JRExporterParameter.JASPER_PRINT, this.jasperPrint);
				  docxexporter.setExporterInput(SimpleExporterInput.getInstance(this.jasperPrintList));
		          //docxexporter.setParameter(JRExporterParameter.OUTPUT_FILE_NAME, this.outputPathName + ".docx");
				  docxexporter.setExporterOutput(new SimpleOutputStreamExporterOutput(outputPathName + ".docx"));
		          docxexporter.exportReport();
		          break;
		      case 1:
		          JROdsExporter odsexporter = new JROdsExporter();
		          //odsexporter.setParameter(JRExporterParameter.JASPER_PRINT, this.jasperPrint);
		          //odsexporter.setParameter(JRExporterParameter.OUTPUT_FILE_NAME, this.outputPathName + ".ods");
		          //odsexporter.setParameter(JRXlsExporterParameter.IS_ONE_PAGE_PER_SHEET, Boolean.TRUE);
		          odsexporter.exportReport();
		          break; 
		      case 2:
		          JROdtExporter odtexporter = new JROdtExporter();
		          //odtexporter.setParameter(JRExporterParameter.JASPER_PRINT, this.jasperPrint);
		          //odtexporter.setParameter(JRExporterParameter.OUTPUT_FILE_NAME, this.outputPathName + ".odt");
		          odtexporter.exportReport();
		          break;
		      case 3:
		          JRRtfExporter rtfexporter = new JRRtfExporter();
		          //rtfexporter.setParameter(JRExporterParameter.JASPER_PRINT, this.jasperPrint);
		          //rtfexporter.setParameter(JRExporterParameter.OUTPUT_FILE_NAME, this.outputPathName + ".rtf");
		          rtfexporter.exportReport();
		          break;
		      case 4:
		          JRXlsExporter xlsexporter = new JRXlsExporter();
		          //xlsexporter.setParameter(JRExporterParameter.JASPER_PRINT, this.jasperPrint);
		          //xlsexporter.setParameter(JRExporterParameter.OUTPUT_FILE_NAME, this.outputPathName + ".xls");
		          //xlsexporter.setParameter(JRXlsExporterParameter.IS_ONE_PAGE_PER_SHEET, Boolean.TRUE);
		          xlsexporter.exportReport();
		          break;
		      case 5:
		          JRXlsxExporter xlsxexporter = new JRXlsxExporter();
		          //xlsxexporter.setParameter(JRExporterParameter.JASPER_PRINT, this.jasperPrint);
		          //xlsxexporter.setParameter(JRExporterParameter.OUTPUT_FILE_NAME, this.outputPathName + ".xlsx");
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
		          //pptxexporter.setParameter(JRExporterParameter.JASPER_PRINT, this.jasperPrint);
		          //pptxexporter.setParameter(JRExporterParameter.OUTPUT_FILE_NAME, this.outputPathName + ".pptx");
		          pptxexporter.exportReport();
		          break;
		      case 7:
		          JRXhtmlExporter xhtmlexporter = new JRXhtmlExporter();
		          //xhtmlexporter.setParameter(JRExporterParameter.JASPER_PRINT, this.jasperPrint);
		          //xhtmlexporter.setParameter(JRExporterParameter.OUTPUT_FILE_NAME, this.outputPathName + ".html");
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
				  pdfexporter.setExporterOutput(new SimpleOutputStreamExporterOutput(outputPathName + ".pdf"));
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
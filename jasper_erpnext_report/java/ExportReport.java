
import java.io.File;

import net.sf.jasperreports.engine.JRException;
import net.sf.jasperreports.engine.JRExporterParameter;
import net.sf.jasperreports.engine.JasperPrint;
import net.sf.jasperreports.engine.JasperFillManager;
import net.sf.jasperreports.engine.export.JRPdfExporter;
import net.sf.jasperreports.engine.export.JRRtfExporter;
import net.sf.jasperreports.engine.export.JRXlsExporter;

import net.sf.jasperreports.engine.export.JRXlsExporterParameter;
import net.sf.jasperreports.engine.export.JRHtmlExporterParameter;
import net.sf.jasperreports.engine.export.JRXhtmlExporter;

import net.sf.jasperreports.engine.export.oasis.JROdsExporter;
import net.sf.jasperreports.engine.export.oasis.JROdtExporter;
import net.sf.jasperreports.engine.export.ooxml.JRDocxExporter;
import net.sf.jasperreports.engine.export.ooxml.JRPptxExporter;
import net.sf.jasperreports.engine.export.ooxml.JRXlsxExporter;
import net.sf.jasperreports.export.SimpleExporterInput;
import net.sf.jasperreports.export.SimpleOutputStreamExporterOutput;


import net.sf.jasperreports.engine.data.JRXmlDataSource;
import net.sf.jasperreports.engine.JRDataSource;
import net.sf.jasperreports.engine.JREmptyDataSource;
import net.sf.jasperreports.engine.data.JRTableModelDataSource;
import javax.swing.table.DefaultTableModel;
import net.sf.jasperreports.engine.JRQuery;

import net.sf.jasperreports.engine.util.JRLoader;
import net.sf.jasperreports.engine.JRParameter;
import net.sf.jasperreports.engine.JasperReport;
import net.sf.jasperreports.engine.fill.JRFileVirtualizer;

import net.sf.jasperreports.engine.JRRewindableDataSource;

import java.math.BigDecimal;
import java.util.HashMap;
import java.sql.Connection;
import java.sql.Driver;
import java.sql.DriverManager;
import java.sql.SQLException;

import java.util.Locale;

import java.util.ListIterator;
//import FrappeDataSource;

public class ExportReport
{
	private String path_jasper_file;
	private String reportName;
	private String outputPath;
	private HashMap params;
	private String conn;
	private int type;
	private String lang;
	private int virtua;
	private String[][] tables;
	private String[] columns;
	private String outputPathName;
	private String jasper_path;
	private Connection connection;
	private JasperPrint jasperPrint;
	private JRDataSource dataSource;
	private DefaultTableModel tableModel;
	private JRQuery query;
	private String queryType;
	private String sqlQueryPath;
	private String xmlName;
	private String numberPattern;
	private String datePattern;
	private Boolean batch;
	
	
	
  public ExportReport(HashMap args){
	  this.batch = false;
	  this.path_jasper_file = (String) args.get("path_jasper_file");
	  this.reportName = (String) args.get("reportName");
	  this.outputPath = (String) args.get("outputPath");
	  this.params = (HashMap) args.get("params");
	  this.conn = (String) args.get("conn");
	  this.type = (Integer) args.get("type");
	  this.lang = (String) args.get("lang");
	  this.numberPattern = (String) args.get("numberPattern");
	  this.datePattern = (String) args.get("datePattern");
	  this.virtua = (Integer) args.get("virtua");

	  this.outputPathName = this.outputPath + this.reportName;
	  this.jasper_path = this.path_jasper_file + this.reportName + ".jasper";
	  
	  
  }
  
  public void setQueryType(){
	  
      if ( this.query == null ){
      		this.queryType = "";
      }else{
      		this.queryType = this.query.getLanguage();
			if (!this.queryType.equalsIgnoreCase("XPATH"))
				this.queryType = "SQL";
      }
          
  }
  
  private void make(){
	  
	  this.setParams();
	  this.setQueryType();
	  
	  if(this.tables == null && this.queryType == "SQL"){
	  	this.connect();
		this.getJasperPrint(this.connection);
		
	  }else if(this.tables == null && !this.queryType.equalsIgnoreCase("XPATH")){
	  	this.dataSource = new JREmptyDataSource();
		this.getJasperPrint(this.dataSource);
	  }else if(this.tables == null && this.queryType.equalsIgnoreCase("XPATH")){
		this.sqlQueryPath = this.query.getText();
		String xmlfile = this.path_jasper_file + this.xmlName + ".xml";
		try{
			Locale locale;
			JRXmlDataSource dataSource = new JRXmlDataSource(xmlfile, this.sqlQueryPath );
            dataSource.setDatePattern( this.datePattern );
            dataSource.setNumberPattern( this.numberPattern );
			dataSource.setLocale(new java.util.Locale(this.lang));
			this.getJasperPrint(dataSource);
		} catch (JRException e)
      	{
        	e.printStackTrace();
      	}
	  	
	  }else{
		this.tableModel = new DefaultTableModel(this.tables, this.columns);
	  	this.dataSource = new JRTableModelDataSource(tableModel);
		this.getJasperPrint(this.dataSource);
	  }
	  
	  if (this.batch != true){
	  	 this.makeReport();
		 System.out.println("Done!");
	  }
  }
  
  private void make(FrappeDataSource fds){
	  
	  this.setParams();
	  this.getJasperPrint(fds);
	  if (this.batch != true){
	  	 this.makeReport();
		 System.out.println("Done!");
	  }
  }
  
  public JasperPrint export(FrappeDataSource fds, Boolean batch)
  {
	 this.batch = batch;
	 this.make(fds);
	 return this.jasperPrint;
  }
  
  public JasperPrint export(String[][] data, String[] cols, FrappeDataSource fds, Boolean batch){
	  this.tables = data;
	  this.columns = cols;
	  this.batch = batch;
	  if (fds != null){
	  	this.make(fds);
	  }else{
	  	this.make();
	  }
	  
	  return this.jasperPrint;
	  
  }
  
  public JasperPrint export(Boolean batch)
  {
	 this.batch = batch;
	 this.make();
	 return this.jasperPrint;
  }
  
  public void setParams(){
	  JasperReport report = null;
	  
	  try{
		  if (this.virtua > 0){
			  JRFileVirtualizer fileVirtua = new JRFileVirtualizer(this.virtua, this.path_jasper_file);
			  this.params.put(JRParameter.REPORT_VIRTUALIZER, fileVirtua);
		  }
	  
		  report = (JasperReport) JRLoader.loadObjectFromFile(this.jasper_path);
		  
		  //if datasource is xml then the name of the xml file without extension (.xml)
		  this.xmlName = report.getProperty("XMLNAME");
		  
		  this.params.put(JRParameter.REPORT_LOCALE, new java.util.Locale(this.lang));
		  this.query = report.getQuery();
		  
		  JRParameter[] reportParameters = report.getParameters();
	      for( int j=0; j < reportParameters.length; j++ ){
	          JRParameter jparam = reportParameters[j];

			  if( jparam.getValueClassName().equals( "java.lang.BigDecimal" )){
			      Object param = this.params.get( jparam.getName());
			      this.params.put(jparam.getName(), new BigDecimal( (Double) this.params.get(jparam.getName())));
			  };
			  
		  };
	  }
      catch (JRException e)
      {
        e.printStackTrace();
      }
	
  }
  
  public void makeReport(){
      
	  try{
		  switch(this.type){
		      case 0:
		          JRDocxExporter docxexporter = new JRDocxExporter();
		          docxexporter.setParameter(JRExporterParameter.JASPER_PRINT, this.jasperPrint);
				  //docxexporter.setExporterInput(SimpleExporterInput.getInstance(jasperPrintList));
		          docxexporter.setParameter(JRExporterParameter.OUTPUT_FILE_NAME, this.outputPathName + ".docx");
				  //docxexporter.setExporterOutput(new SimpleOutputStreamExporterOutput(this.outputPathName + ".docx"));
		          docxexporter.exportReport();
		          break;
		      case 1:
		          JROdsExporter odsexporter = new JROdsExporter();
		          odsexporter.setParameter(JRExporterParameter.JASPER_PRINT, this.jasperPrint);
		          odsexporter.setParameter(JRExporterParameter.OUTPUT_FILE_NAME, this.outputPathName + ".ods");
		          odsexporter.setParameter(JRXlsExporterParameter.IS_ONE_PAGE_PER_SHEET, Boolean.TRUE);
		          odsexporter.exportReport();
		          break; 
		      case 2:
		          JROdtExporter odtexporter = new JROdtExporter();
		          odtexporter.setParameter(JRExporterParameter.JASPER_PRINT, this.jasperPrint);
		          odtexporter.setParameter(JRExporterParameter.OUTPUT_FILE_NAME, this.outputPathName + ".odt");
		          odtexporter.exportReport();
		          break;
		      case 3:
		          JRRtfExporter rtfexporter = new JRRtfExporter();
		          rtfexporter.setParameter(JRExporterParameter.JASPER_PRINT, this.jasperPrint);
		          rtfexporter.setParameter(JRExporterParameter.OUTPUT_FILE_NAME, this.outputPathName + ".rtf");
		          rtfexporter.exportReport();
		          break;
		      case 4:
		          JRXlsExporter xlsexporter = new JRXlsExporter();
		          xlsexporter.setParameter(JRExporterParameter.JASPER_PRINT, this.jasperPrint);
		          xlsexporter.setParameter(JRExporterParameter.OUTPUT_FILE_NAME, this.outputPathName + ".xls");
		          xlsexporter.setParameter(JRXlsExporterParameter.IS_ONE_PAGE_PER_SHEET, Boolean.TRUE);
		          xlsexporter.exportReport();
		          break;
		      case 5:
		          JRXlsxExporter xlsxexporter = new JRXlsxExporter();
		          xlsxexporter.setParameter(JRExporterParameter.JASPER_PRINT, this.jasperPrint);
		          xlsxexporter.setParameter(JRExporterParameter.OUTPUT_FILE_NAME, this.outputPathName + ".xlsx");
		          xlsxexporter.setParameter(JRXlsExporterParameter.IS_ONE_PAGE_PER_SHEET, Boolean.TRUE);
		          xlsxexporter.exportReport();
		          break;
		      /*case "jxl":
		          JRExcelApiExporter exporter = new JRExcelApiExporter();
		          exporter.setParameter(JRExporterParameter.OUTPUT_FILE_NAME, reportName + ".rtf");
		          exporter.setParameter(JRXlsExporterParameter.IS_ONE_PAGE_PER_SHEET, Boolean.TRUE);
		          break;*/
		      case 6:
		          JRPptxExporter pptxexporter = new JRPptxExporter();
		          pptxexporter.setParameter(JRExporterParameter.JASPER_PRINT, this.jasperPrint);
		          pptxexporter.setParameter(JRExporterParameter.OUTPUT_FILE_NAME, this.outputPathName + ".pptx");
		          pptxexporter.exportReport();
		          break;
		      case 7:
		          JRXhtmlExporter xhtmlexporter = new JRXhtmlExporter();
		          xhtmlexporter.setParameter(JRExporterParameter.JASPER_PRINT, this.jasperPrint);
		          xhtmlexporter.setParameter(JRExporterParameter.OUTPUT_FILE_NAME, this.outputPathName + ".html");
		          //xhtmlexporter.setParameter(JRHtmlExporterParameter.IS_OUTPUT_IMAGES_TO_DIR, Boolean.TRUE);
		          //xhtmlexporter.setParameter(JRHtmlExporterParameter.IMAGES_URI, "./");
		          //xhtmlexporter.setParameter(JRHtmlExporterParameter.IMAGES_DIR_NAME, "./images/");
		          xhtmlexporter.exportReport();
		          break;
		      case 8:
		      default:
		          JRPdfExporter pdfexporter = new JRPdfExporter();
		          pdfexporter.setParameter(JRExporterParameter.JASPER_PRINT, this.jasperPrint);
				  //pdfexporter.setExporterInput(SimpleExporterInput.getInstance(jasperPrintList));
				  //pdfexporter.setExporterOutput(new SimpleOutputStreamExporterOutput(this.outputPathName + ".pdf"));
		          pdfexporter.setParameter(JRExporterParameter.OUTPUT_FILE_NAME, this.outputPathName + ".pdf");
		          pdfexporter.exportReport();
		          break;
		  }
	  }
      catch (JRException e)
      {
        e.printStackTrace();
      }
		
  }

	public void connect(){
  		
	    try
	    {
			Class.forName("org.mariadb.jdbc.Driver");
			this.connection = DriverManager.getConnection(this.conn);
		}
	    catch (ClassNotFoundException e){
	        e.printStackTrace();
	    }
		catch (SQLException e){
		      e.printStackTrace();
		}
  }
  
	public void getJasperPrint(Connection connection){
	 try{
		this.jasperPrint = JasperFillManager.fillReport(this.jasper_path, this.params, connection);
	  }
      catch (JRException e)
      {
        e.printStackTrace();
      }
  	}
  
	public void getJasperPrint(JRDataSource dataSource){
		
	 try{
		this.jasperPrint = JasperFillManager.fillReport(this.jasper_path, this.params, dataSource);
	  }
	    catch (JRException e)
	    {
	      e.printStackTrace();
	    }
	}
}

import java.util.List;
import java.util.ArrayList;
import java.util.HashMap;
import net.sf.jasperreports.engine.JasperPrint;

public class BatchReport
{
	private int type;
	private String outputPathName;
	private String fileName;
	private List<JasperPrint> jasperPrintList;
	
	
	public BatchReport(){
		this.jasperPrintList = new ArrayList<JasperPrint>();
	}
	
	public BatchReport(int type, String outputPathName){
		this.jasperPrintList = new ArrayList<JasperPrint>();
		this.type = type;
		this.outputPathName = outputPathName;
	}
	
	public void setType(int type){
		this.type = type;
	}
	
	public void setFileName(String fname){
		this.fileName = fname;
	}
	
	public void setOutputPath(String outputPathName){
		this.outputPathName = outputPathName;
	}
	
	public void addToBatch(HashMap args, String[][] data, String[] cols, FrappeDataSource fds){
		ExportReport exporter = new ExportReport(args);
		JasperPrint jasperPrint =  exporter.export(data, cols, fds, true);
		this.jasperPrintList.add(jasperPrint);
	}
	
	public void export(){
		MakeReport mr = new MakeReport(this.jasperPrintList);
		mr.makeReport(this.type, this.outputPathName, this.fileName);
	}
	
}
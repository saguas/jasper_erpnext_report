import java.util.List;
import java.util.ArrayList;
import java.util.HashMap;
import net.sf.jasperreports.engine.JasperPrint;

public class BatchReport
{
	private int type;
	private String outputPathName;
	private String fileName;
	private String opasswd;
	private String upasswd;
	private boolean encrypt;
	private List<JasperPrint> jasperPrintList;
	private IFrappeTask Task;
	
	
	public BatchReport(){
		this.jasperPrintList = new ArrayList<JasperPrint>();
	}
	
	public BatchReport(int type, String outputPathName, IFrappeTask task){
		this.jasperPrintList = new ArrayList<JasperPrint>();
		this.type = type;
		this.encrypt = false;
		this.opasswd = "pdf";
		this.upasswd = "pdf";
		this.outputPathName = outputPathName;
		this.Task = task;
	}

	public void setTaskHandler(IFrappeTask task){
		this.Task = task;
	}

	public void setType(int type){
		this.type = type;
	}
	
	public void setFileName(String fname){
		this.fileName = fname;
	}
	
	public void setUserPassword(String upasswd){
		this.upasswd = upasswd;
	}
	
	public void setOwnerPassword(String opasswd){
		this.opasswd = opasswd;
	}
	
	public void encrypt(boolean encrypt){
		this.encrypt = encrypt;
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
		MakeReport mr = new MakeReport(this.jasperPrintList, this.encrypt, this.opasswd, this.upasswd);
		mr.makeReport(this.type, this.outputPathName, this.fileName);
		this.Task.setReadyTask();
	}
	
}
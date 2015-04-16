import java.io.File;
import net.sf.jasperreports.engine.JasperCompileManager;
import net.sf.jasperreports.engine.JRException;


public class ReportCompiler {
	
    public void compile(String reportName, String destFileName)
    {
		try {
			System.out.println("Compiling report... reportName " + reportName + " destFileName " + destFileName);
			System.out.println("Working Directory = " + System.getProperty("user.dir"));
			JasperCompileManager.compileReportToFile(reportName, destFileName);
			System.out.println("Done!");
		}catch (JRException e){
			e.printStackTrace();
		}
	}
	
	public static void main(String[] args)
	{
		new ReportCompiler().compile(args[0],args[1]);
	}
}

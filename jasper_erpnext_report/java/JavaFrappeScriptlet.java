import net.sf.jasperreports.engine.JRAbstractScriptlet;
import net.sf.jasperreports.engine.JRScriptletException;


public class JavaFrappeScriptlet extends JRAbstractScriptlet {

	private IFrappeScriptlet Sl;

	public void setFrappeScriptlet(IFrappeScriptlet scl){
		this.Sl = scl;
	}

	public void beforeReportInit() throws JRScriptletException {
		this.Sl.beforeReportInit();
	}

	public void afterReportInit() throws JRScriptletException {
		this.Sl.afterReportInit();
	}

	public void beforePageInit() throws JRScriptletException {
		this.Sl.beforePageInit();
	}

	public void afterPageInit() throws JRScriptletException {
		this.Sl.afterPageInit();
	}

	public void beforeColumnInit() throws JRScriptletException {
		this.Sl.beforeColumnInit();
	}

	public void afterColumnInit() throws JRScriptletException {
		this.Sl.afterColumnInit();
	}

	public void beforeGroupInit(String gname) throws JRScriptletException {
		this.Sl.beforeGroupInit(gname);
	}

	public void afterGroupInit(String gname) throws JRScriptletException {
		this.Sl.afterGroupInit(gname);
	}

	public void beforeDetailEval() throws JRScriptletException {
		this.Sl.beforeDetailEval();
	}

	public void afterDetailEval() throws JRScriptletException {
		this.Sl.afterDetailEval();
	}

	public Object callPythonMethod(String methodName, Object... args) {
		return this.Sl.callPythonMethod(methodName, args);
	}

}
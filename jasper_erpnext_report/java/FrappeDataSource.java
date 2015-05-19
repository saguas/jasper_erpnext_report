import net.sf.jasperreports.engine.JRException;
import net.sf.jasperreports.engine.JRField;
import net.sf.jasperreports.engine.JRRewindableDataSource;


public class FrappeDataSource implements JRRewindableDataSource
{

  private IFrappeDataSource list;

  public FrappeDataSource(IFrappeDataSource list)
  {
	  this.list = list;
  }

  public boolean next() throws JRException
  {
    boolean retVal = true;

    retVal = this.list.next();

    return retVal;
  }

  public Object getFieldValue(JRField field) throws JRException
  {
	String name = field.getName();
	String ret = this.list.getFieldValue(name);
	return ret;
  }

  public void moveFirst() throws JRException
  {
    this.list.moveFirst();
  }
}

import java.io.FileNotFoundException;
import java.io.IOException;
import java.util.ListIterator;
import net.sf.jasperreports.engine.JRException;
import net.sf.jasperreports.engine.JRField;
import net.sf.jasperreports.engine.JRRewindableDataSource;

//import IFrappeDataSource;

public class FrappeDataSource implements JRRewindableDataSource
{
  private int currentRowIndex = -1;
  private int currentColIndex = 0;
  private int totalRows;
  private IFrappeDataSource list;

  public FrappeDataSource(IFrappeDataSource list)
  {
	  this.list = list;
	  System.out.println("in FrappeDataSource Constructor ");
  }

  public boolean next() throws JRException
  {
    boolean retVal = true;

    retVal = this.list.next();
	System.out.println("in next retVal is: " + retVal);

    return retVal;
  }

  public Object getFieldValue(JRField field) throws JRException
  {
	String name = field.getName();
    System.out.println("in getFieldValue: " + name);
	String ret = this.list.getFieldValue(name);
	return ret;
  }

  public void moveFirst() throws JRException
  {
    currentRowIndex = 0;
    currentColIndex = 0;
	System.out.println("in moveFirst: ");
  }
}

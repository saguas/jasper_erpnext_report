interface IFrappeScriptlet {

   public void beforeReportInit();
   public void afterReportInit();
   public void beforePageInit();
   public void afterPageInit();
   public void beforeColumnInit();
   public void afterColumnInit();
   public void beforeGroupInit(String gname);
   public void afterGroupInit(String gname);
   public void beforeDetailEval();
   public void afterDetailEval();
   public Object callPythonMethod(String methodName, Object... args);

}
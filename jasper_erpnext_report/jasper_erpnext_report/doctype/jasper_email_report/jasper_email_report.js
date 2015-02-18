frappe.provide("jasper");


cur_frm.cscript.refresh = function(doc){
	if (doc.__islocal === 1)
		hide_field(["get_report"]);
};

cur_frm.cscript["get_report"] = function(doc, dt, dn){
    email_doc = frappe.get_doc("Jasper Email Report", dn);
    console.log("get_reports ", doc, dt, dn);
    console.log("get_docs ", email_doc);
    if (doc.__islocal !== 1)
    	jasper.getJasperEmailReport(email_doc.jasper_report_path, email_doc.jasper_file_name);
};



jasper.getJasperEmailReport = function(filepath, filename){

    var reqdata = {filepath: filepath, filename: filename};
    var request = "/api/method/jasper_erpnext_report.core.JasperWhitelist.get_jasper_email_report?data="+encodeURIComponent(JSON.stringify(reqdata));
    console.log("request ", request)
    w = window.open(request);
	if(!w) {
		msgprint(__("Please enable pop-ups"));
	}
};

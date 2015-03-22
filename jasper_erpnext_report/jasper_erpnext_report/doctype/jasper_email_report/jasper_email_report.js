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
	var ext = jasper.get_extention_name(filename);
	var request = "";
	if (ext === "html" || ext === "pdf"){
		request = frappe.urllib.get_base_url() + "/" + encodeURI(filepath);
	}else{
		var reqdata = {filepath: filepath, filename: filename};
    	request = "/api/method/jasper_erpnext_report.core.JasperWhitelist.get_jasper_email_report?data="+encodeURIComponent(JSON.stringify(reqdata));
	}

    console.log("request ", request)
    w = window.open(request,"_self");
	if(!w) {
		msgprint(__("Please enable pop-ups"));
	}
};

jasper.get_extention_name = function(filename){
	var ext = "pdf";
	var arr = filename.split(".");
	if (arr.length > 0){
		ext = arr[arr.length - 1];
	}

	return ext;
}

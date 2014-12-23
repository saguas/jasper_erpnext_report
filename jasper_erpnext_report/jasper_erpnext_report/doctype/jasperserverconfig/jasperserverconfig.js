$(document).on("jasper_ready",function(){
	console.log("sid apos app_ready event ", frappe.get_cookie("sid"));
	if(!frappe.jasper_reports_list){
		frappe.call({
			"method": "jasper_erpnext_report.core.jaspersession.get_reports_list",
			callback: function (data) {
				console.log("get_reports_list ", data);
				if(data.message){
					console.log("resultado: ", data.message);
					frappe.boot['jasper_reports_list'] = data.message
				}
			
			}
		});
	
		frappe.call({
			"method": "jasper_erpnext_report.core.jaspersession.get_server_info",
			callback: function (data) {
				console.log("get_server_info ", data);
				if(data.message){
					console.log("resultado: ", data.message);
					frappe.boot['jasper_server_info'] = data.message
				}
			
			}
		});
	};
});


cur_frm.cscript.refresh = function(doc){
    
    //$(cur_frm.get_field("query_html").wrapper).find('.query').text('luis')
    //this.set_value("query_html", "12234");
    var timeout = " To change Jasper Session expire time, please go to <code><strong>Setup->Settings->System Settings</strong></code>" 
                    + " and change the field Jasper Session Expiry. Note that you must first change the"
                    +"value in the Jasper Server.";
    var code = '<div class="panel panel-default">'
                 + '<div class="panel-heading">'
                    + '<h3 class="panel-title">Server Timeout Value</h3>'
                 + '</div>'
                 + '<div class="panel-body">'
                 + '<p class="bs-callout bs-callout-danger">' + '<span class="label label-danger">Note:</span>' + timeout + '</p>'
                 + '</div>'
        + '</div>';

    //cur_frm.fields_dict.query_html.$wrapper.html("<div class='panel panel-primary'><pre class='bg-warning'>" + doc.query + "</pre></div>")
        cur_frm.fields_dict.jasper_server_timeout_html.$wrapper.html(code);
        cur_frm.cscript.serverInfo(doc);
        console.log("query: ", code);
}

cur_frm.cscript.serverInfo = function(doc){
    arr_info = doc.jasper_server_name.split("\n")
    /*var code = '<div class="panel panel-default">'
                 + '<div class="panel-heading">'
                    + '<h3 class="panel-title">Server Timeout Value</h3>'
                 + '</div>'
                 + '<div class="panel-body">'
                    + '<pre class="bs-callout bs-callout-info">' + doc.jasper_server_name + '</pre>'
                 + '</div>'
              + '</div>';*/
    
    var code = '<div class="panel panel-default">'
                     + '<div class="panel-heading">'
                        + '<h3 class="panel-title">Server Information</h3>'
                     + '</div>'
                     + '<div class="panel-body">'
                    +'<pre class="bs-callout bs-callout-info">';
    
      for (i=0;i<arr_info.length;i++){
          var a = arr_info[i].split(":");
          code = code + "<strong>"+ a[0] + "</strong>";
          for (j=1;j<a.length;j++){
                code = code + "<strong>:</strong>"  + a[j];
          }
          
          code = code + "<br>";
      };
      code = code + '</pre>';
      code = code + '</div>';
      code = code + '</div>';
    
    cur_frm.fields_dict.server_info_html.$wrapper.html(code);
}

cur_frm.cscript.custom_validate = function(doc) {

	this.register_event_save();
	
	//var args = {name:"luis", idade:45};
    var args = {report_name:"Cherry", doctype:"Jasper Reports", name_ids:["Administrator"], pformat:"pdf"};
	
    console.log("validate called ");
	//jasper.get_jasper_report("/reports/erpnext/Leaf_Red_Table_Based", "run_report","pdf", args);
    
    //jasper.run_jasper_report("run_report", args, null);
    
    //jasper.get_jasper_report("get_report", args, null);
	
    //validated = false;
	/*var args = {name:"luis", idade:45};
	
	var w = window.open("/api/method/jasper_erpnext_report.core.jaspersession.run_report?"
	+ "path=" + encodeURIComponent("/reports/erpnext/Leaf_Red_Table_Based")
	+ "&data=" + JSON.stringify(args)
	+ "&format=" + "pdf"
	);
	if (!w) {
		msgprint(__("Please enable pop-ups"));
		return;
	};*/
	
};

cur_frm.cscript.register_event_save = function(){
	var self = this;
	
	$(document).one("save", function(event, arrdoc){
		if (arrdoc.doctype === "JasperServerConfig" )
			//$(document).trigger("jasper_ready")
            a = 1
		else
			self.register_event_save()
	});
};

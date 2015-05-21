
jasper.get_jasper_server_info = function(){
	frappe.call({
		"method": "jasper_erpnext_report.core.JasperWhitelist.get_server_info",
		callback: function (data) {
			if(data.message){
				frappe.boot['jasper_server_info'] = data.message
			}
		
		}
	});
}

jasper.jasper_server_connect = function(doc){
	var deferred = jQuery.Deferred();
	frappe.call({
		freeze: true,
		freeze_message: "Connecting...",
        args:{"doc":doc},
		"method": "jasper_erpnext_report.core.JasperWhitelist.jasper_server_login",
		callback: function (data) {
			if(data.message && data.message !== "Not connected!"){
				deferred.resolve(data.message);
			}else{
				deferred.reject();
			}
		
		}
	});
	
	return deferred;
}

cur_frm.cscript.jasper_connect_update_btn = function(doc){
	var deferred = jasper.jasper_server_connect(doc);
	deferred.done(function(data){
		var info = [];
		server_info = JSON.parse(data);
		for(var k in server_info){
			info.push(k+": "+server_info[k]);
		};
		var infostr = info.join("\n");
		doc.jasper_server_name = infostr;
		cur_frm.cscript.serverInfo(doc);
		msgprint(__("Connect/Update Done!"), __("Jasper Report Configuration"));
	})
	.fail(function() {
		msgprint(__("Error to Connect/Update to Jasper Reports Server."), __("Jasper Report Configuration"));
  });
}

cur_frm.cscript.refresh = function(doc){

    var timeout = __(" To change Jasper Session expire time, please go to <code><strong>Setup->Settings->System Settings</strong></code>"
                    + " and change the field Jasper Session Expiry. Note that you must first change the"
                    +"value in the Jasper Server.");
    var code = '<div class="panel panel-default">'
                 + '<div class="panel-heading">'
                    + '<h3 class="panel-title">' + __("Server Timeout Value") + '</h3>'
                 + '</div>'
                 + '<div class="panel-body">'
                 + '<p class="bs-callout bs-callout-danger">' + '<span class="label label-danger">Note:</span>' + timeout + '</p>'
                 + '</div>'
        + '</div>';

        cur_frm.fields_dict.jasper_server_timeout_html.$wrapper.html(code);
        cur_frm.cscript.serverInfo(doc);
        cur_frm.cscript.show_fields(doc);
}

cur_frm.cscript.serverInfo = function(doc){
    arr_info = doc.jasper_server_name;
    if (arr_info){
	arr_info = arr_info.split("\n");
    }else{
	arr_info = [];
    }
    
    var code = '<div class="panel panel-default">'
                     + '<div class="panel-heading">'
                        + '<h3 class="panel-title">' + __("Server Information") + '</h3>'
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

cur_frm.cscript.use_jasper_server = function(doc, val){
	cur_frm.cscript.show_fields(doc);
};


cur_frm.cscript.show_fields = function(doc){
	if (doc.use_jasper_server === "Local jrxml only" || doc.use_jasper_server === "None"){
		hide_field(["jasper_server_url","jasper_report_root_path", "jasper_username", "jasper_server_password",
		 "jasper_connect_update_btn", "import_all_reports", "import_only_new", "server_info_html",
		 "jasper_session_timeout"]);
	}else{
		unhide_field(["jasper_server_url","jasper_report_root_path", "jasper_username", "jasper_server_password",
		 "jasper_connect_update_btn", "import_all_reports", "import_only_new", "server_info_html",
		 "jasper_session_timeout"]);
	}
}

frappe.provide("jasper");

cur_frm.cscript.refresh = function(doc){
    var cs = cur_frm.cscript;
    //$(cur_frm.get_field("query_html").wrapper).find('.query').text('luis')
    //this.set_value("query_html", "12234");
    //fortype can be "doctype" or "report"
    //var args = {fortype: "doctype", report_name:"Teste 1", doctype:"Jasper Reports", name_ids:["Administrator", "Guest"], pformat:"pdf"};
    //var df = jasper.run_jasper_report("run_report", args, null);
    
    //cur_frm.conn_test();
    
    cs.show_fields(doc);
    
    var query = doc.query != undefined? doc.query:""
    var code = '<div class="panel panel-default">'
                 + '<div class="panel-heading">'
                    + '<h3 class="panel-title">SQL</h3>'
                 + '</div>'
                 + '<div class="panel-body">'
                        + '<pre class="bs-callout-bg bs-callout-warning-bg">' + query + '</pre>'
                 + '</div>'
             + '</div>'

    //cur_frm.fields_dict.query_html.$wrapper.html("<div class='panel panel-primary'><pre class='bg-warning'>" + doc.query + "</pre></div>")
    cur_frm.fields_dict.query_html.$wrapper.html(code)
    console.log("query: ", code)
}

cur_frm.cscript["jasper_report_origin"] = function(doc, dt, dn){
    var origin = doc.jasper_report_origin;
    if (origin === "JasperServer"){
        hide_field(["jasper_upload_jrxml", "report_images:", "jasper_all_sites_report"]);
        if (doc.__islocal){
            cur_frm.set_value("jasper_report_path", "");
        }
        unhide_field(["jasper_report_path"]);
    }else if(doc.__islocal){//never saved
        hide_field(["jasper_upload_jrxml", "report_images:", "jasper_report_path"]);
        cur_frm.set_value("jasper_report_path", "/");
    }else{
        unhide_field(["jasper_upload_jrxml", "report_images:", "jasper_all_sites_report"]);
        hide_field(["jasper_report_path"]);
    }
}

cur_frm.cscript.show_fields = function(doc){
    var origin = doc.jasper_report_origin;
    console.log("never saved ", doc.__islocal);
    if (origin === "JasperServer"){
        //cur_frm.set_df_property("jasper_upload_jrxml", "hidden", "True");
        hide_field(["jasper_upload_jrxml", "report_images:", "jasper_all_sites_report"]);
        //cur_frm.set_df_property("jasper_report_images", "hidden", "True");
    }else if(doc.__islocal){//never saved
        hide_field(["jasper_upload_jrxml", "report_images:", "jasper_report_path"]);
        //doc.jasper_report_path = "/";
        cur_frm.set_value("jasper_report_path", "/");
        //cur_frm.refresh_field("jasper_report_path");
    }else{
        hide_field(["jasper_report_path"]);
    }
    
};

//frappe.ui.form.on("Jasper Reports", "save", function(frm) {
//cur_frm.cscript["save"] = function(doc, dt, dn){
$(document).on("save", function(ev, doc){
	var cs = cur_frm.cscript;
	if(doc.__islocal === 1){
		//cs.show_fields(doc);
		unhide_field(["jasper_upload_jrxml", "report_images:", "jasper_all_sites_report"]);
    }
});

cur_frm.cscript.onload = function(doc){
    //$('.query').text("luis filipe")
    //cur_frm.fields_dict.query_html.$wrapper.html("<p>Luis</p>")
    //var cs = cur_frm.cscript;
    //cs.show_fields(doc);
}

//this is for testing liveupdates with threads, pubsub and queue
//must be ajax because green progress line in desk
cur_frm.conn_test = function(){
    var opts = {};
    var ajax_args = {
    	url: opts.url || frappe.request.url,
        data:{cmd: "jasper_erpnext_report.jasper_reports.run_local_report.conn_test"},
    	type: 'POST',
    	dataType: opts.dataType || 'json',
    	async: opts.async
    };
    $.ajax(ajax_args).done(
        function(response_data){
            console.log("conn_test response ", response_data);
        }
    );
    
    /*frappe.call({
	       "method": "jasper_erpnext_report.jasper_reports.run_local_report.conn_test",
           args: {},
           progress_bar: 0,
           show_spinner: 1,
	       callback: function(response_data){
			   console.log("conn_test response ", response_data);
		   }
     });*/
    
};


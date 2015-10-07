frappe.provide("jasper");

jasper.pending_reports = [];

jasper.poll_count = 0;

pending_banner = [];

jasper_report_formats = {pdf:"icon-file-pdf", "docx": "icon-file-word", doc: "icon-file-word", xls:"icon-file-excel", xlsx:"icon-file-excel", 
						/*ppt:"icon-file-powerpoint", pptx:"icon-file-powerpoint",*/ odt: "icon-file-openoffice", ods: "icon-libreoffice",
	 					rtf:"fontello-icon-doc-text", email: "icon-envelope-alt", submenu:"icon-grid"};

async_func_callback = function(data){
	console.log("subscribe data ", data);
	var banner_data = pending_banner.pop()
	var $banner = banner_data.banner;
	var timeout = banner_data.timeout;

	var result = data.result;
	if (result.origin === "local"){
		var reqids = [];
	    for(var i=0; i<result.length; i++){
	        reqids.push(result[i].requestId);
	    };
	    var poll_data = [{reqIds: reqids, reqtime: result[0].reqtime, pformat: result[0].pformat, origin: result[0].origin}]
		jasper.pending_reports.push(result);
		//setTimeout(jasper.jasper_report_ready, 1000*10, poll_data, $banner, timeout);
		jasper.jasper_report_ready(poll_data, $banner, timeout);
	}else{
		if (result.status === "ready"){
           jasper.pending_reports.push(result);
           setTimeout(jasper.jasper_report_ready, 1000*10, result, $banner, timeout);
        }else{
           jasper.polling_report(result, $banner, timeout);
        }
     }
	delete frappe.socket.open_tasks[data.task_id];
}

queued_func_callback = function(data){
	console.log("queued data ", data);
	frappe.socket.subscribe("Local-" + data.task_id, {callback:async_func_callback});
}

jasper.run_jasper_report = function(method, data, doc){
    var df = new $.Deferred();
    $banner = jasper.show_banner(__("Please wait. System is processing your report. It will notify you when ready."));
    timeout = setTimeout(jasper.close_banner, 1000*15, $banner);
    pending_banner.push({banner:$banner, timeout:timeout});

    frappe.call({
	       "method": "jasper_erpnext_report.core.JasperWhitelist." + method,
	       queued: queued_func_callback,
	       args:{
               data: data,
	           docdata: doc
	       }/*,
	       callback: function(response_data){
               if (response_data && response_data.message){
                   var msg = response_data.message;
                   var task_id = response_data.task_id;
               }
		    }*/
     });
     
     return df;
};

jasper.get_task_status = function(task_id){

	frappe.call({
	       "method": "frappe.async.get_task_status",
	       args:{
               task_id: task_id,
	       },
	       callback: function(response_data){
               //if (response_data && response_data.message){
               console.log(response_data);
               //}
            }
	});
}

jasper.polling_report = function(data, $banner, timeout){
    var reqids = [];
    for(var i=0; i<data.length; i++){
        reqids.push(data[i].requestId);
    };
    var poll_data = {reqIds: reqids, reqtime: data[0].reqtime, pformat: data[0].pformat, origin: data[0].origin}
    //check only one
    frappe.call({
	       "method": "jasper_erpnext_report.core.JasperWhitelist.report_polling",
	       args:{
               data: poll_data,
	       },
	       callback: function(response_data){
               if (response_data && response_data.message){
                   var msg = response_data.message;
                   if (msg[0].status === "ready"){
					   jasper.poll_count = 0;
                       jasper.jasper_report_ready(msg, $banner, timeout);
                   }else if (!msg[0].status && !msg[0].error){
					   if (jasper.poll_count <= 9 ){
						   jasper.poll_count++;
						   var ptime = parseInt(frappe.boot.jasper_reports_list && frappe.boot.jasper_reports_list.jasper_polling_time);
						   setTimeout(jasper.polling_report, ptime, data, $banner, timeout);
						   return;
					   };
                       jasper.poll_count = 0;
                       jasper.close_banner($banner);
                       var banner_msg = __("Timeout before report is ready to download. Click to ") + '<a class="try_again_report">'+__("Try Again")+'</a>'
                       + "  " +'<a class="cancel_report">Cancel</a>';
                       show_banner_message(banner_msg, ".try_again_report", ".cancel_report", "#FFFF99", function($banner, what){
                           jasper.close_banner($banner);
                           if (what === "ok"){
                               var ptime = parseInt(frappe.boot.jasper_reports_list && frappe.boot.jasper_reports_list.jasper_polling_time);
                               var $banner = jasper.show_banner(__("Please wait. System is processing your report. It will notify you when ready."));
                               var timeout = setTimeout(jasper.close_banner, 1000*15, $banner);
							   jasper.polling_report(data, $banner, timeout);
                           }
                       });
                   }else{
					   jasper.poll_count = 0;
                       msgprint(msg[0].error || msg[0].value, __("Report error."));
                       jasper.close_banner($banner);
                   }
               }
		   }
     });
};


jasper.jasper_report_ready = function(msg, $old_banner, timeout){
    $old_banner.find(".close").click();
    clearTimeout(timeout);
    var banner_msg = __("Your report is ready to download. Click to ") + '<a class="download_report">'+__("download")+'</a>';
    show_banner_message(banner_msg, ".download_report", null, "lightGreen", function($banner){
        jasper.getReport(msg);
		jasper.close_banner($banner);
    });
};



jasper.getReport = function(msg){
 
	var reqdata = msg[0];
    var w;
    if (reqdata.pformat === "html" || reqdata.pformat === "pdf"){
        frappe.call({
	       "method": "jasper_erpnext_report.core.JasperWhitelist.get_report",
	       args:{
               data: JSON.stringify(reqdata),
	       },
	       callback: function(response_data){
			   w = window.open(frappe.urllib.get_base_url() + "/" + encodeURI(response_data.message), "_self");
           	   if(!w) {
           		   msgprint(__("Please enable pop-ups."));
           	   }
               return;
           }
       });
    }else{
        var request = "/api/method/jasper_erpnext_report.core.JasperWhitelist.get_report?data="+encodeURIComponent(JSON.stringify(reqdata));
        w = window.open(request);
    	if(!w) {
    		msgprint(__("Please enable pop-ups."));
    	}
    }
    
};

jasper.getListOnly = function(page, doctype, docnames){

	var dfd = jQuery.Deferred();

	if (!docnames)
		docnames = [];
	
	method = "jasper_erpnext_report.core.JasperWhitelist.get_reports_list";
	data = {doctype: doctype, docnames: docnames, report: null};
	jasper.jasper_make_request(method, data,function(response_data){
		jasper.pages[page] = response_data.message;
		dfd.resolve();
	})

	return dfd.promise();
}

jasper.getList = function(page, doctype, docnames){
	var jpage = frappe.pages[page];
	if(jpage && jasper.pages[page]){
		list = jasper.pages[page];
		setJasperDropDown(list, jasper.getOrphanReport);
	}else{
		method = "jasper_erpnext_report.core.JasperWhitelist.get_reports_list";
		data = {doctype: doctype, docnames: docnames, report: null};
		jasper.jasper_make_request(method, data,function(response_data){
			jasper.pages[page] = response_data.message;
			setJasperDropDown(response_data.message, jasper.getOrphanReport);
		});
	};
};

jasper.getQueryReportList = function(query_report){
	if(jasper.report[query_report]){
		list = jasper.report[query_report];
		setJasperDropDown(list, jasper.getOrphanReport);
	}else{
		method = "jasper_erpnext_report.core.JasperWhitelist.get_reports_list";
		data = {doctype: null, docnames: null, report: query_report};
		jasper.jasper_make_request(method, data,function(response_data){
			jasper.report[query_report] = response_data.message;
			setJasperDropDown(response_data.message, jasper.getOrphanReport);
		});
	};
};

$(window).on('hashchange', function() {
	var route = frappe.get_route();
	var len = route.length;
	var doctype, docname;
	var list = {};
	var callback;

	jasper.getCountryCode();
	
	if (len > 2 && route[0] === "Form"){
		var method;
		var data;
		doctype = route[1];
		docname = route[2];
		doc_new = docname.search("New");
		if (doc_new === -1 || doc_new > 0){
            var page = jasper.get_page();
			jasper.getList(page, doctype, [docname]);
			return;
		}
	}else if(len > 1 && route[0] === "List"){
		doctype = route[1];
        var page = jasper.get_page();
		jasper.getList(page, doctype, []);
		return;
	}else if(((len > 1 && (route[0] === "query-report" || route[0] === "Report")) || (len === 1 && route[0] !== ""))){
        if (len > 1){
            report_name = route[1];
        }else{
            report_name = route[0];
        }
		jasper.getQueryReportList(report_name);
		return;
	}else if(route[0] === ""){
		list = frappe.boot.jasper_reports_list;
		callback = jasper.getOrphanReport;
	}
	setJasperDropDown(list, callback);
	
});

jasper.get_doc = function(doctype, docname){
    var df = new $.Deferred();
    var doctype = doctype || "Jasper Reports"
	var method = "jasper_erpnext_report.core.JasperWhitelist.get_doc";
    var data = {doctype: doctype, docname: docname};
    jasper.jasper_make_request(method, data, function(response_data){
        df.resolve(response_data['data']);
    });
    
    return df;
};

setJasperDropDown = function(list, callback){
	$(".dropdown.jasper_report_list_menu").remove();
	if (list && !$.isEmptyObject(list) && list.size > 0){
		var size = list.size;
		
		var html = '<li class="dropdown jasper_report_list_menu">'
			+ '<a class="dropdown-toggle" href="#" data-toggle="dropdown" title="Jasper Reports" onclick="return false;">'
				+ '<span><img src="/assets/jasper_erpnext_report/images/jasper_icon.png" style="max-width: 24px; max-height: 24px; margin: -2px 0px;">  </img></span>'
		 + '<span> <span class="badge" id="jrcount">' + size +'</span></span></span></a>'
			+ '<ul class="dropdown-menu jrmenu">';

			var flen;
			var icon_file;
		    list = jasper.sortObject(list);
			for(var key in list){
				if(list[key] !== null && typeof list[key] === "object"){
					flen = list[key].formats.length;
					var skey = jasper.shorten(key, 35);
					html = html + jasper.make_menu(list, key, skey);
				};
			};
		
			html = html + '</ul></li>';
			
			function clicked(ev){
				ev.preventDefault();
				var data = $(ev.target).data();
				var jr_format = data.jr_format;
				var jr_name = data.jr_name;
				callback({jr_format: data.jr_format, jr_name: data.jr_name, list: list}, ev);
			};
			
			$(".nav.navbar-nav.navbar-right").append(html)
			$(".nav.navbar-nav.navbar-right .jrreports").on("click", clicked);
	};
		
};

jasper.getOrphanReport = function(data, ev){
	var route = frappe.get_route();
	var len = route.length;
	var docids;
    var docname = data.doctype_type;
    var fortype = "doctype";
    var grid_data = null;
    var columns = null;
    var rtype = "General";
    var cur_doctype = data.doctype;

	var docids = data.docids;
	//if (len > 1 && route[0] === "List"){
	//	var doctype = route[1];
	//	var page = [route[0], doctype].join("/");
	//	docids = jasper.getCheckedNames(page);
	if (!docids){
		docids = jasper.getIdsFromList();
		if(docids){
	        docname = route[0];
			if (docids.length === 0)
			{
				msgprint(__("Please, select at least one name."), __("Jasper Report"));
				return;
			};
			cur_doctype = route[1];
		}else{ //if(len > 2 && route[0] === "Form"){
			docids = jasper.getIdsFromForm();
			//if (cur_frm){
			if (docids){
				docids = [docids];
			//	docids = [cur_frm.doc.name];
	            docname = route[0];
	            cur_doctype = route[1];
			//}else{
			//	msgprint(__("To print this document you must be in a form."), __("Jasper Report"));
			//	return;
			//}
			}else if((len > 1 && (route[0] === "query-report" || route[0] === "Report")) || (len === 1 && route[0] !== "")){
				fortype = "query-report";
				columns = jasper.query_report_columns();
				grid_data = jasper.query_report_data();
				if (len === 1){
					docname = route[0];
				}else{
					docname = route[1];
				}
				cur_doctype = docname;
			}
		}
	}
    var params;
    jasper.check_for_ask_param(data.jr_name, data.page, function(obj){
        if (!obj || obj && obj.abort === true)
            return;

        if (!data.list){
			data.list = frappe.boot.jasper_reports_list;
		}
        var jr_format = data.jr_format;
		var params = obj.values || {};
		if (params.locale !== undefined && params.locale !== null){
			params.locale = jasper.get_alpha3(params.locale);
		}else {
			var jr_name = data.jr_name;
			var doc = data.list[jr_name];
			if(doc.jasper_report_origin === "LocalServer"){
				params.locale = jasper.get_alpha3(doc.locale);
			}
		}
    	var args = {fortype: fortype, report_name: data.jr_name, doctype:"Jasper Reports", cur_doctype: cur_doctype, name_ids: docids, pformat: jr_format, params: params, is_doctype_id: obj.is_doctype_id, grid_data: {columns: columns, data: grid_data}};
        if(jr_format === "email"){
        	var version = jasper.get_app_version("frappe");
        	if (version >= "5"){
        		jasper.email_doc_v5("Jasper Email Doc", cur_frm, args, data.list, docname);
        	}else{
        		jasper.email_doc("Jasper Email Doc", cur_frm, args, data.list, docname);
        	}

        }else{
            jasper.run_jasper_report("run_report", args, docname);
        }
    });
};

jasper.jasper_make_request = function(method, data, callback){

    frappe.call({
	       method: method,
	       args: data,
	       callback: callback
     });
};

$(document).on( 'app_ready', function(){
	$(window).trigger('hashchange');
});



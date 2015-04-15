frappe.provide("jasper");

jasper.pending_reports = [];

jasper.poll_count = 0;

jasper.pages = {};
jasper.report = {};

jasper_report_formats = {pdf:"icon-file-pdf", "docx": "icon-file-word", doc: "icon-file-word", xls:"icon-file-excel", xlsx:"icon-file-excel", 
						/*ppt:"icon-file-powerpoint", pptx:"icon-file-powerpoint",*/ odt: "icon-file-openoffice", ods: "icon-libreoffice",
	 					rtf:"fontello-icon-doc-text", email: "icon-envelope-alt", submenu:"icon-grid"};

/*
jasper.download = function(url, data, method){
    //url and data options required
    if( url && data ){
        //data can be string of parameters or array/object
        data = typeof data == 'string' ? data : jQuery.param(data);
        //split params into form inputs
        var inputs = '';
        jQuery.each(data.split('&'), function(){
            var pair = this.split('=');
            inputs+='<input type="hidden" name="'+ pair[0] +'" value="'+ pair[1] +'" />';
        });
        //send request
        jQuery('<form target="_blank" action="'+ url +'" method="'+ (method||'post') +'">'+inputs+'</form>')
        .appendTo('body').submit().remove();
        
        console.log("sented request %s %s args %s", url, inputs)
    };
};
*/
/*
//jasper.get_jasper_report = function(path, method, format, data){
jasper.get_jasper_report = function(method, data, doc, type){
    //var format = format || 'pdf';
    //var args = 'path='+ encodeURIComponent(path) +'&format='+ format;
    var args = "";
    if (data){
        args = args + 'data=' + encodeURIComponent(JSON.stringify(data));
        console.log("args ", args);
    };
    
    if (doc){
        args = args + '&doc=' + encodeURIComponent(JSON.stringify(doc));
    };
    
    if(type){
        args = args + '&type=' + type;
    };
    
	jasper.download("/api/method/jasper_erpnext_report.core.JasperWhitelist." + method, args);
};
*/
jasper.run_jasper_report = function(method, data, doc){
    var df = new $.Deferred();
    frappe.call({
	       "method": "jasper_erpnext_report.core.JasperWhitelist." + method,
	       args:{
               data: data,
	           docdata: doc
	       },
	       callback: function(response_data){
               if (response_data && response_data.message){
                   var msg = response_data.message;
                   if (msg[0].status === "ready"){
                       $banner = frappe.ui.toolbar.show_banner(__("Please wait. System is processing your report. It will notify you when is ready."))
                       timeout = setTimeout(jasper.close_banner, 1000*15, $banner);
                       jasper.pending_reports.push(msg);
                       setTimeout(jasper.jasper_report_ready, 1000*10, msg, $banner, timeout);
                   }else{
                       $banner = frappe.ui.toolbar.show_banner(__("Please wait. System is processing your report. It will notify you when is ready."))
                       timeout = setTimeout(jasper.close_banner, 1000*15, $banner);
                       jasper.polling_report(msg, $banner, timeout);
                   }
               }
		   }
     });
     
     return df;
};

//TODO: must be tested!!!
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
                   }else if (!msg[0].status){
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
							   jasper.polling_report(data, $banner, timeout);
                           }
                       });
                   }else{
					   jasper.poll_count = 0;
                       msgprint(msg[0].value, __("Report error."));
                   }
               }
		   }
     });
};

jasper.close_banner = function($banner){
    $banner.find(".close").click();
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

show_banner_message = function(msg, where_ok, where_cancel, bckcolor, callback){
    $banner = frappe.ui.toolbar.show_banner(msg);
    if (bckcolor != null)
        $banner.css({background: bckcolor, opacity: 0.9});
    if (where_ok != null){
	    $banner.find(where_ok).click(function(){
            callback($banner, "ok");
        });
    };
    
    if(where_cancel != null){
    	$banner.find(where_cancel).click(function(){
            callback($banner, "cancel");
        }); 
    };
}

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

jasper.get_page = function(){
    var route = frappe.get_route();
	var doctype = route[1];
	var page = [route[0], doctype].join("/");
    return page;
};

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
	
	$("#jasper_report_list").remove();
	
	if (list && !$.isEmptyObject(list) && list.size > 0){
		var size = list.size;
		
		var html = '<li class="dropdown" id="jasper_report_list">'
			+ '<a class="dropdown-toggle" href="#" data-toggle="dropdown" title="Jasper Reports" onclick="return false;">'
				+ '<span><img src="assets/jasper_erpnext_report/images/jasper_icon.png" style="max-width: 24px; max-height: 24px; margin: -2px 0px;">  </img></span>' 
		 + '<span> <span class="badge" id="jrcount">' + size +'</span></span></span></a>'
			+ '<ul class="dropdown-menu" id="jrmenu">';

			var flen;
			var icon_file;
		    list = sortObject(list);
			for(var key in list){
				if(list[key] !== null && typeof list[key] === "object"){
					flen = list[key].formats.length;
					var skey = shorten(key, 35);
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

jasper.get_jasperdoc_from_name = function(rname, rpage){
    var robj = frappe.boot.jasper_reports_list && frappe.boot.jasper_reports_list[rname];
    if (robj === undefined || robj === null){
		var page = rpage;
		if (!page){
			page = jasper.get_page();
		}
        robj = jasper.pages[page];
		if (robj){
			robj = jasper.pages[page][rname];
		};
    }
    if (robj === undefined || robj === null){
        var route = frappe.get_route();
        var len = route.length;
        var r;
        if (len > 1)
            r = route[1];
        else
            r = route[0];
        if(jasper.report[r])
			robj = jasper.report[r][rname];
    }
    
    if (robj === undefined || robj === null)
        return
	
	return robj;
}

jasper.check_for_ask_param = function(rname, callback){
    var robj = jasper.get_jasperdoc_from_name(rname);
    console.log("Is doctype id? ", robj);
    var ret;
    if (robj.locale === "Ask" || robj.params && robj.params.length > 0){
        ret = jasper.make_dialog(robj, rname + " parameters", callback);
    }else{
        callback({abort: false});
    }
};

jasper.make_menu = function(list, key, skey){
	var f = list[key].formats;
    var email = list[key].email;
	var mail_enabled = list.mail_enabled;
	var icon_file = [];
	var html = "";
	for(var i=0; i < f.length; i++){
		var type = f[i];
		icon_file.push(repl('<i title="%(title)s" data-jr_format="%(f)s" data-jr_name="%(mykey)s" class="jasper-%(type)s"></i>', {title:key + " - " + type, mykey:key, f:f[i], type: jasper_report_formats[type]}));
	};
    if (email === 1 && mail_enabled === 1){
        icon_file.push(repl('<i title="%(title)s" data-jr_format="%(f)s" data-jr_name="%(mykey)s" class="%(type)s"></i>', {title: "send by email", mykey:key, f:"email", type: jasper_report_formats["email"]}));
    }
	html = html + '<li>'
       + repl('<a class="jrreports" href="#" data-jr_format="%(f)s" data-jr_name="%(mykey)s"',{mykey:key, f:"html"}) +' title="'+ key +' - html" >'+ icon_file.join(" ") + " " + skey  + '</a>' 
 	   +'</li>';
	 
	return html;
};

jasper.getOrphanReport = function(data, ev){
	var route = frappe.get_route();
	var len = route.length;
	var docids;
    var docname;
    var fortype = "doctype";
    var grid_data = null;
    var columns = null;
    var rtype = "General";
    



	//if (len > 1 && route[0] === "List"){
	//	var doctype = route[1];
	//	var page = [route[0], doctype].join("/");
	//	docids = jasper.getCheckedNames(page);
	docids = jasper.getIdsFromList();
	if(docids){
        docname = route[0];
		if (docids.length === 0)
		{
			msgprint(__("Please, select at least one name."), __("Jasper Report"));
			return;
		};
	}else{ //if(len > 2 && route[0] === "Form"){
		docids = jasper.getIdsFromForm();
		//if (cur_frm){
		if (docids){
			docids = [docids];
		//	docids = [cur_frm.doc.name];
         docname = route[0];
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
		}
	}
    var params;
    jasper.check_for_ask_param(data.jr_name, function(obj){
        if (!obj || obj && obj.abort === true)
            return;
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
    	var args = {fortype: fortype, report_name: data.jr_name, doctype:"Jasper Reports", name_ids: docids, pformat: jr_format, params: params, is_doctype_id: obj.is_doctype_id, grid_data: {columns: columns, data: grid_data}};
        if(jr_format === "email"){
            jasper.email_doc("Jasper Email Doc", cur_frm, args, data.list, docname);
        }else{
            jasper.run_jasper_report("run_report", args, docname);
        }
    });
};


function shorten(text, maxLength) {
    var ret = text;
    if (ret.length > maxLength) {
        ret = ret.substr(0,maxLength-3) + "...";
    }
    return ret;
}

function sortObject(o) {
    var sorted = {},
    key, a = [];

    for (key in o) {
    	if (o.hasOwnProperty(key)) {
    		a.push(key);
    	}
    }

    a.sort();

    for (key = 0; key < a.length; key++) {
    	sorted[a[key]] = o[a[key]];
    }
    return sorted;
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

jasper.make_dialog = function(doc, title, callback){
	
    var fields = [];
	var params = doc.params;
	var docids = null;

	for (var i=0; i < params.length; i++){
		var param = doc.params[i];
		if (param.is_copy === "Is doctype id"){
			docids = jasper.getIdsFromList();
			if(!docids)
				docids = cur_frm && cur_frm.doc.name;
		};
		fields.push({label:param.name, fieldname:param.name, fieldtype:param.jasper_param_type==="String"? "Data": param.jasper_param_type,
		 	description:param.jasper_param_description || "", default:param.jasper_param_value || docids});
	};
	if(doc.jasper_report_origin === "LocalServer"){
		var lang_default = frappe.defaults.get_user_default("language");
		fields.push({label:__("Locale"), fieldname:"locale", fieldtype: "Select",
	 		description: __("Select the report language."), options: jasper.make_country_list(), default:[lang_default]});
	};

	function ifyes(d){
        if (callback){
            callback({values: d.get_values(), abort: false, is_doctype_id: docids === null?false:true});
        }
	};
	function ifno(){
        if (callback){
            callback({abort: true});
        }
	};

	var d = jasper.ask_dialog(title, doc.message, fields, ifyes, ifno);
	return d;
}

jasper.getIdsFromList = function(){
	var docids = null;
	var route = frappe.get_route();
	var len = route.length;
	if (len > 1 && route[0] === "List"){
		var doctype = route[1];
		var page = [route[0], doctype].join("/");
		docids = jasper.getCheckedNames(page);
	}

	return docids;
};

jasper.getIdsFromForm = function(){
	var docids = null;
	var route = frappe.get_route();
	var len = route.length;
	if(len > 2 && route[0] === "Form"){
		docids = cur_frm && cur_frm.doc.name;
	}

	return docids;
}

jasper.getCountryCode = function(){
	jasper.CountryCode = frappe.boot.langinfo;
};

jasper.make_country_list = function(){
	if (jasper.CountryList && jasper.CountryList.length > 0){
		return jasper.CountryList;
	};
	if (!jasper.CountryCode || jasper.CountryCode.length == 0){
		jasper.getCountryCode();
	};
		
	jasper.CountryList = [];
	for (var i=0; i<jasper.CountryCode.length;i++){
		jasper.CountryList.push(jasper.CountryCode[i].name);
	};
	
	return jasper.CountryList;
};

jasper.get_alpha3 = function(locale){
	if (!jasper.CountryCode || jasper.CountryCode.length === 0)
		return;
	
	var alpha3;
	
	for (var i=0; i<jasper.CountryCode.length;i++){
		if (jasper.CountryCode[i].name === locale){
			alpha3 = jasper.CountryCode[i].code;
			break;
		};
	};
	
	return alpha3;
};

jasper.ask_dialog = function(title, message, fields, ifyes, ifno) {
	var html = {fieldtype:"HTML", options:"<p class='frappe-confirm-message'>" + message + "</p>"};
	fields.splice(0,0,html);
	var d = new frappe.ui.Dialog({
		title: __(title),
		fields: fields,
		primary_action: function() { d.hide(); ifyes(d); }
	});
	d.show();
	if(ifno) {
		d.$wrapper.find(".modal-footer .btn-default").click(ifno);
	}
	return d;
}

jasper.getChecked = function(name){
	return $(frappe.pages[name]).find("input:checked");
}

jasper.getCheckedNames = function(page){
	var names = [];
	var checked = jasper.getChecked(page);
	var elems_a = checked.siblings("a");
	elems_a.each(function(i,el){
		var t = unescape($(el).attr("href")).slice(1);
		var s = t.split("/");
		names.push(s[s.length - 1]);
	});
	
	return names;
}

// jasper_doc
jasper.email_doc = function(message, curfrm, jasper_doc, list, route0) {
    
    if (curfrm){
    	new jasper.CommunicationComposer({
    		doc: curfrm.doc,
    		subject: __(curfrm.meta.name) + ': ' + curfrm.docname,
    		recipients: curfrm.doc.email || curfrm.doc.email_id || curfrm.doc.contact_email,
    		attach_document_print: true,
    		message: message,
    		real_name: curfrm.doc.real_name || curfrm.doc.contact_display || curfrm.doc.contact_name,
            jasper_doc: jasper_doc,
	        docdata: route0,
            list: list
    	});
    }else{
    	new jasper.CommunicationComposer({
    		doc: {doctype: jasper_doc.doctype, name: jasper_doc.report_name},
    		subject: jasper_doc.doctype + ': ' + jasper_doc.report_name,
    		recipients: undefined,
    		attach_document_print: false,
    		message: message,
    		real_name: "",
            jasper_doc: jasper_doc,
	        docdata: route0,
            list: list
    	});
    }
}

jasper.query_report_columns = function(){
    var columns = [];
    var cols = frappe.query_report.grid.getColumns();
    var len = cols.length;
    for(var i=0; i<len; i++){
        columns.push({name: cols[i].name, field: cols[i].field});
    }
    
    return columns;
}

jasper.query_report_data = function(){
    var items = [];
    var sg = frappe.query_report.grid;
    if (sg){
        var dl = sg.getDataLength();
        for (var i=0; i<dl;i++){
            items.push(sg.getDataItem(i))
        }
    }
    
    return items;
}

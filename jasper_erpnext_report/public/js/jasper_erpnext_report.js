frappe.provide("jasper");

jasper.pending_reports = [];

jasper.poll_count = 0;

jasper.pages = {};
jasper.report = {};

jasper_report_formats = {pdf:"icon-file-pdf", "docx": "icon-file-word", doc: "icon-file-word", xls:"icon-file-excel", xlsx:"icon-file-excel", 
						/*ppt:"icon-file-powerpoint", pptx:"icon-file-powerpoint",*/ odt: "icon-file-openoffice", ods: "icon-libreoffice",
	 					rtf:"fontello-icon-doc-text", email: "icon-envelope-alt", submenu:"icon-grid"};

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

//jasper.run_jasper_report = function(method, data, doc, type){
jasper.run_jasper_report = function(method, data, doc){
    //var format = format || 'pdf';
    //var args = 'path='+ encodeURIComponent(path) +'&format='+ format;
    var df = new $.Deferred();
    frappe.call({
	       "method": "jasper_erpnext_report.core.JasperWhitelist." + method,
	       args:{
               data: data,
	           docdata: doc
               //rtype: type
	       },
	       callback: function(response_data){
			   console.log("resolved ", response_data);
               if (response_data && response_data.message){
                   var msg = response_data.message;
                   if (msg[0].status === "ready"){
                       //var reqdata = {reqId: msg.requestId, expId: msg.ids[0].id, fileName: msg.ids[0].fileName};
                       //console.log("reqdata ", reqdata)
                       //jasper.get_jasper_report("get_report", reqdata, null, null);
                       //df.resolve(msg);
                       $banner = frappe.ui.toolbar.show_banner(__("Please wait while i'm processing your report. I will notify you when is ready!"))
                       timeout = setTimeout(jasper.close_banner, 1000*15, $banner);
                       jasper.pending_reports.push(msg);
                       console.log("setting timeout!!!");
                       //jasper.jasper_report_ready(msg, $banner, timeout)
                       setTimeout(jasper.jasper_report_ready, 1000*10, msg, $banner, timeout);
                       //jasper.print("get_report", reqdata);
                   }else{
                       console.log("polling_report!!!");
                       $banner = frappe.ui.toolbar.show_banner(__("Please wait while i'm processing your report. I will notify you when is ready!"))
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
			   console.log("polling response ", response_data);
               console.log("local report ready!!! ", response_data.message[0].status);
               if (response_data && response_data.message){
                   var msg = response_data.message;
                   if (msg[0].status === "ready"){
					   jasper.poll_count = 0;
                       jasper.jasper_report_ready(msg, $banner, timeout);
                   }else if (!msg[0].status){
                       //setTimeout(jasper.polling_report, 1000*5, data, $banner, timeout);
					   console.log("polling not ready count ", jasper.poll_count);
					   if (jasper.poll_count <= 9 ){
						   jasper.poll_count++;
						   var ptime = parseInt(frappe.boot.jasper_reports_list.jasper_polling_time);
						   console.log("ptime ", ptime);
						   setTimeout(jasper.polling_report, ptime, data, $banner, timeout);
						   return;
					   };
                       jasper.poll_count = 0;
                       jasper.close_banner($banner);
                       var banner_msg = __("Timeout before report is ready to download! Click to ") + '<a class="try_again_report">Try Again</a>' 
                       + "  " +'<a class="cancel_report">Cancel</a>';
                       show_banner_message(banner_msg, ".try_again_report", ".cancel_report", "#FFFF99", function($banner, what){
                           jasper.close_banner($banner);
                           if (what === "ok"){
                               var ptime = parseInt(frappe.boot.jasper_reports_list.jasper_polling_time);
                               //setTimeout(jasper.polling_report, ptime, data, $banner, timeout);
							   jasper.polling_report(data, $banner, timeout);
                           }
                       });
					   
                       //msgprint(msg[0].value, __("Report error! The report is taking too long... "));
                       //jasper.polling_report(data, $banner, timeout);
                   }else{
					   jasper.poll_count = 0;
                       msgprint(msg[0].value, __("Report error "));
                   }
               }
		   }
     });
};

jasper.close_banner = function($banner){
    $banner.find(".close").click();
};

jasper.jasper_report_ready = function(msg, $old_banner, timeout){
    //$old_banner = $('header .navbar').find(".toolbar-banner");
    $old_banner.find(".close").click();
    clearTimeout(timeout);
    var banner_msg = __("Your report is ready to download! Click to ") + '<a class="download_report">download</a>';
    show_banner_message(banner_msg, ".download_report", null, "lightGreen", function($banner){
        jasper.getReport(msg);
		jasper.close_banner($banner);
    });
    /*$banner = frappe.ui.toolbar.show_banner(__("Your report is ready to download! Click to ") + '<a class="download_report">download</a>')
    $banner.css({background: "lightGreen", opacity: 0.9});
	$banner.find(".download_report").click(function() {
        jasper.getReport(msg);
		jasper.close_banner($banner);
	});*/
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
    console.log("this reqdata ", reqdata)
    var w;
    if (reqdata.pformat === "html" || reqdata.pformat === "pdf"){
        console.log("is html");
        frappe.call({
	       "method": "jasper_erpnext_report.core.JasperWhitelist.get_report",
	       args:{
               data: JSON.stringify(reqdata),
	       },
	       callback: function(response_data){
			   console.log("polling response ", response_data);
               console.log("local report ready!!! ", response_data.message);
               //w = window.open(frappe.urllib.get_base_url() + "/assets/" + encodeURI(response_data.message));
			   w = window.open(frappe.urllib.get_base_url() + "/" + encodeURI(response_data.message), "_self");
               //var c = "/assets/" + response_data.message;
               //console.log("colorbox ", c)
               //$.colorbox({href: encodeURIComponent(c), opacity: 0.8, width: "90%", height: "90%"});
           	   if(!w) {
           		   msgprint(__("Please enable pop-ups"));
                   //return;
           	   }
               /*w.document.open();
               var basehtml = document.createElement('base');
               var base = frappe.urllib.get_base_url() + "/assets/jasper_erpnext_report/reports/site1.local/Accounts Report/images/>";
               basehtml.href = base;
               w.document.getElementsByTagName('head')[0].appendChild(basehtml);
               w.document.write(response_data.message);
               w.document.close();*/
               //w.document.write("<base href='" + base + "'");
               return;
           }
       });
    }else{
        var request = "/api/method/jasper_erpnext_report.core.JasperWhitelist.get_report?data="+encodeURIComponent(JSON.stringify(reqdata));
        console.log("request ", request)
        w = window.open(request);
    	if(!w) {
    		msgprint(__("Please enable pop-ups"));
    	}
    }
    
};

jasper.getList = function(page, doctype, docnames){
	var jpage = frappe.pages[page];
	console.log("jasper.getList docnames ", docnames, doctype);
	if(jpage && jasper.pages[page]){
		list = jasper.pages[page];
		//console.log("exist lista ", list);
		setJasperDropDown(list, jasper.getOrphanReport);
	}else{
		method = "jasper_erpnext_report.core.JasperWhitelist.get_reports_list";
		data = {doctype: doctype, docnames: docnames, report: null};
		console.log("pedido for doctype %s docname %s ", doctype, docnames);
		jasper.jasper_make_request(method, data,function(response_data){
			console.log("resposta for doctype docname ", response_data, jpage, page);
			//frappe.pages[page]["jasper"] = response_data.message;
			jasper.pages[page] = response_data.message;
			setJasperDropDown(response_data.message, jasper.getOrphanReport);
		});
	};
};

jasper.getQueryReportList = function(query_report){
	if(jasper.report[query_report]){
		list = jasper.report[query_report];
		//console.log("exist lista ", list);
		setJasperDropDown(list, jasper.getOrphanReport);
	}else{
		method = "jasper_erpnext_report.core.JasperWhitelist.get_reports_list";
		data = {doctype: null, docnames: null, report: query_report};
		console.log("pedido for report %s ", query_report);
		jasper.jasper_make_request(method, data,function(response_data){
			console.log("resposta for doctype docname ", response_data);
			//frappe.pages[page]["jasper"] = response_data.message;
			jasper.report[query_report] = response_data.message;
			setJasperDropDown(response_data.message, jasper.getOrphanReport);
		});
	};
};

$(window).on('hashchange', function() {
	var route = frappe.get_route();
	console.log("hashchange !!", route);
	var len = route.length;
	var doctype, docname;
	var list = {};
	var callback;
	
	console.log("route ", len)
	jasper.getCountryCode();
	
	if (len > 2 && route[0] === "Form"){
		var method;
		var data;
		doctype = route[1];
		docname = route[2];
		doc_new = docname.search("New");
		if (doc_new === -1 || doc_new > 0){
			//var page = [route[0], doctype].join("/");
            var page = jasper.get_page();
			jasper.getList(page, doctype, [docname]);
			return;
		}
	}else if(len > 1 && route[0] === "List"){
		doctype = route[1];
		//var page = [route[0], doctype].join("/");
        var page = jasper.get_page();
		//jasper.setEventClick(page);
		console.log("page ", page);
		//docnames = jasper.getCheckedNames(page);
		//if(docnames.length > 0){
		jasper.getList(page, doctype, []);
		return;
		/*}else{
			msgprint(__("Please, select at list one name"), __("Jasper Report"));
		}*/
		
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
		//setJasperDropDown(list);
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
        console.log("resposta for doctype docname ", response_data);
        df.resolve(response_data['data']);
    });
    
    return df;
};

/*setJasperDropDownWithSubMenus = function(list, callback){
	
	$("#jasper_report_list").remove();
	
	if (list && !$.isEmptyObject(list) && list.size > 0){
		var size = list.size;
		
		var html = '<li class="dropdown" id="jasper_report_list">'
			+ '<a class="dropdown-toggle" href="#" data-toggle="dropdown" title="Jasper Reports" onclick="return false;">'
				+ '<span><img src="assets/jasper_erpnext_report/images/jasper_icon.png" style="max-width: 24px; max-height: 24px; margin: -2px 0px;">  </img></span>' 
		 + '<span> <span class="badge" id="jrcount">' + size +'</span></span></span></a>'
			+ '<ul class="dropdown-menu" id="jrmenu">';
	
			//var jq = $("#jrcount", html).text(size)
			//console.log("jq ", jq)
			var flen;
			var icon_file;
		    list = sortObject(list);
			for(var key in list){
				if(key !== "size"){
					flen = list[key].formats.length;
					var skey = shorten(key, 35);
					if(flen === 1){
						html = html + jasper.make_menu(list, key, skey, 0);
					}else{
						html = html + jasper.make_submenu(skey);
						for(var i = 0; i < flen; i++){
							html = html + jasper.make_menu(list, key, skey, i);
						};
						html = html + "</ul></li>"
					};
				};
			};
		
			html = html + '</ul></li>';
			//console.log("html ", html)
			$(".nav.navbar-nav.navbar-right").append(html)
			$(".nav.navbar-nav.navbar-right .jrreports").on("click", callback);
	};
		
};*/


setJasperDropDown = function(list, callback){
	
	$("#jasper_report_list").remove();
	
	if (list && !$.isEmptyObject(list) && list.size > 0){
		var size = list.size;
		
		var html = '<li class="dropdown" id="jasper_report_list">'
			+ '<a class="dropdown-toggle" href="#" data-toggle="dropdown" title="Jasper Reports" onclick="return false;">'
				+ '<span><img src="assets/jasper_erpnext_report/images/jasper_icon.png" style="max-width: 24px; max-height: 24px; margin: -2px 0px;">  </img></span>' 
		 + '<span> <span class="badge" id="jrcount">' + size +'</span></span></span></a>'
			+ '<ul class="dropdown-menu" id="jrmenu">';
	
			//var jq = $("#jrcount", html).text(size)
			//console.log("jq ", jq)
			var flen;
			var icon_file;
		    list = sortObject(list);
			for(var key in list){
				//if(key !== "size" || key !="jasper_polling_time"){
				if(list[key] !== null && typeof list[key] === "object"){
					flen = list[key].formats.length;
					var skey = shorten(key, 35);
					html = html + jasper.make_menu(list, key, skey);
				};
			};
		
			html = html + '</ul></li>';
			//console.log("html ", html);
			
			function clicked(ev){
				ev.preventDefault();
				//ev.stopPropagation();
				/*if (last_menu_report){
					$(last_menu_report).popover('hide')
				};
				last_menu_report = ev.currentTarget;
				*/
				console.log("data from ev: ", ev.target);
				var data = $(ev.target).data();
				var jr_format = data.jr_format;
				var jr_name = data.jr_name;
				console.log("jr_format ", jr_format, jr_name, list);
				//$(".nav.navbar-nav.navbar-right").popover({content:"teste content ", title:"popover jasper", placement:"left"});
				
				//$(ev.currentTarget).popover({content:"teste content ", title:"popover jasper", placement:"right"});
				//$(ev.currentTarget).popover('show');
				callback({jr_format: data.jr_format, jr_name: data.jr_name, list: list}, ev);
			};
			
			$(".nav.navbar-nav.navbar-right").append(html)
			//$(".nav.navbar-nav.navbar-right").prepend(html)
			$(".nav.navbar-nav.navbar-right .jrreports").on("click", clicked);
	};
		
};

jasper.get_jasperdoc_from_name = function(rname, rpage){
    var robj = frappe.boot.jasper_reports_list[rname];
    if (robj === undefined){
		var page = rpage;
		if (!page){
			page = jasper.get_page();
		}
        robj = jasper.pages[page];
		if (robj){
			robj = jasper.pages[page][rname];
		};
    }
    if (robj === undefined){
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
    
    if (robj === undefined)
        return
	
	return robj;
}

jasper.check_for_ask_param = function(rname, callback){
    var robj = jasper.get_jasperdoc_from_name(rname);
    var ret;
    if (robj.locale === "Ask" || robj.params && robj.params.length > 0){
        ret = jasper.make_dialog(robj, rname + " parameters", callback);
    }else{
        callback({abort: false});
    }
    
    console.log("ret: ", ret);
};

jasper.make_menu = function(list, key, skey){
	//jasper_report_formats[list[key].formats[0]]
	var f = list[key].formats;
    var email = list[key].email;
	var mail_enabled = list.mail_enabled;
	console.log("mail_enabled ", mail_enabled);
	//var t = list[key].formats.join(":");
	var icon_file = [];
	var html = "";
	for(var i=0; i < f.length; i++){
		var type = f[i];
		icon_file.push(repl('<i title="%(title)s" data-jr_format="%(f)s" data-jr_name="%(mykey)s" class="jasper-%(type)s"></i>', {title:key + " - " + type, mykey:key, f:f[i], type: jasper_report_formats[type]}));
	};
    if (email === 1 && mail_enabled === 1){
        console.log("email ", email);
        icon_file.push(repl('<i title="%(title)s" data-jr_format="%(f)s" data-jr_name="%(mykey)s" class="%(type)s"></i>', {title: "send by email", mykey:key, f:"email", type: jasper_report_formats["email"]}));
    }
	//data-jr_format='+ t + ' data-jr_name="'+ key + '" class="jrreports"
	html = html + '<li>'
 	   //+ repl('<a class="jrreports" href="#" data-jr_format="%(f)s" data-jr_name="%(mykey)s"',{mykey:key, f:f[0]}) +' title="'+ key +' - pdf" >'+ icon_file.join(" ") + " " + skey  + '</a>' 
       + repl('<a class="jrreports" href="#" data-jr_format="%(f)s" data-jr_name="%(mykey)s"',{mykey:key, f:"html"}) +' title="'+ key +' - html" >'+ icon_file.join(" ") + " " + skey  + '</a>' 
 	   +'</li>';
	 
	return html;
};

/*jasper.make_submenu = function(skey){
	//jasper_report_formats[list[key].formats[0]]
	var html = '<li class="dropdown-submenu">'
		+ '<a tabindex="-1" href="#">'+ skey +'</a>'
		+ '<ul class="dropdown-menu">';

	 return html;
};*/

jasper.getOrphanReport = function(data, ev){
	var route = frappe.get_route();
	var len = route.length;
	var docids;
    var docname;
    var fortype = "doctype";
    var grid_data = null;
    var columns = null;
    var rtype = "General";
    
    
	if (len > 1 && route[0] === "List"){
		var doctype = route[1];
		var page = [route[0], doctype].join("/");
		docids = jasper.getCheckedNames(page);
        docname = route[0];
        //rtype = route[0];
		if (docids.length === 0)
		{
			msgprint(__("Please, select at list one name"), __("Jasper Report"));
			return;
		};
	}else if(len > 2 && route[0] === "Form"){
		if (cur_frm){
			docids = [cur_frm.doc.name];
            docname = route[0];
            //rtype = route[0];
		}else{
			msgprint(__("To print this doc you must be in a form."), __("Jasper Report"));
			return;
		}
	}else if((len > 1 && (route[0] === "query-report" || route[0] === "Report")) || (len === 1 && route[0] !== "")){
        fortype = "query-report";
        columns = jasper.query_report_columns();
        grid_data = jasper.query_report_data();
        if (len === 1){
            //rtype = jasper.report[route[0]][data.jr_name].jasper_report_type;
            docname = route[0];
        }else{
            //rtype = jasper.report[route[1]][data.jr_name].jasper_report_type;
            docname = route[1];
        }
        //docnames = ["Administrator"];
	}
    var params;
    jasper.check_for_ask_param(data.jr_name, function(obj){
        console.log("docids ", docids);
        if (obj && obj.abort === true)
            return;
        var jr_format = data.jr_format;
		var params = obj.values || {};
		console.log("obj.values ", params, data);
		if (params.locale !== undefined && params.locale !== null){
			params.locale = jasper.get_alpha3(params.locale);
		}else {
			var jr_name = data.jr_name;
			var doc = data.list[jr_name];
			console.log("params not ask get value ", doc);
			if(doc.jasper_report_origin === "LocalServer"){
				params.locale = jasper.get_alpha3(doc.locale);
			}
		}
    	var args = {fortype: fortype, report_name: data.jr_name, doctype:"Jasper Reports", name_ids: docids, pformat: jr_format, params: params, grid_data: {columns: columns, data: grid_data}};
        if(jr_format === "email"){
            //jasper.email_doc("Jasper Email Doc", cur_frm, args, data.list, docname, rtype);
            jasper.email_doc("Jasper Email Doc", cur_frm, args, data.list, docname);
        }else{
            //jasper.run_jasper_report("run_report", args, docname, rtype);
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
    console.log("frappe is ready ", jasper);
	$(window).trigger('hashchange');
    //var list = frappe.boot.jasper_reports_list;
	/*setJasperDropDown(list, function(data, ev){
		console.log("was clicked !! ", $(ev.target).data())
		jasper.getOrphanReport(data, ev);
	});*/
});

jasper.make_dialog = function(doc, title, callback){
	function ifyes(d){
		console.log("ifyes return ", d.get_values());
        if (callback){
            callback({values: d.get_values(), abort: false});
        }
	};
	function ifno(){
		console.log("ifno return ");
        if (callback){
            callback({abort: true});
        }
	};
	
    var fields = [];
	//var fields = [{label:"teste 1", fieldname:"teste 1", fieldtype:"Data"}, {label:"teste2", fieldname:"teste 2", fieldtype:"Check", description:"choose one"}];
	var params = doc.params;
	for (var i=0; i < params.length; i++){
		var param = doc.params[i];
		fields.push({label:param.name, fieldname:param.name, fieldtype:param.jasper_param_type=="String"? "Data": param.jasper_param_type,
		 	description:param.jasper_param_description || "", default:param.jasper_param_value});
	};
	console.log("origin:", doc);
	if(doc.jasper_report_origin === "LocalServer"){
		var lang_default = frappe.defaults.get_user_default("language");
		fields.push({label:__("Locale"), fieldname:"locale", fieldtype: "Select",
	 		description: __("Select the report language"), options: jasper.make_country_list(), default:[lang_default]});
	};
	var d = jasper.ask_dialog(title, doc.message, fields, ifyes, ifno);
	return d;
}

jasper.getCountryCode = function(){
	jasper.CountryCode = frappe.boot.langinfo;
	/*if(jasper.CountryCode && jasper.CountryCode.length > 0){
		return;
	};
	method = "jasper_erpnext_report.core.JasperWhitelist.get_jrxml_locale";
	var data = {};
	jasper.jasper_make_request(method, data,function(response_data){
		console.log("resposta for doctype docname ", response_data);
		//frappe.pages[page]["jasper"] = response_data.message;
		jasper.CountryCode = response_data.message;
	});*/
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
		//console.log("alpha3 ", jasper.CountryCode[i].name, locale, jasper.CountryCode[i].alpha3);
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
//jasper.email_doc = function(message, curfrm, jasper_doc, list, route0, route1) {
jasper.email_doc = function(message, curfrm, jasper_doc, list, route0) {
    //var args = {fortype: "doctype", report_name: data.jr_name, doctype:"Jasper Reports", name_ids: docnames, pformat: data.jr_format, params: d};
    
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
            //rtype: route1,
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
            //rtype: route1,
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


//jasper.dialog_upload = Class.extend({
jasper.dialog_upload = frappe.ui.form.ControlData.extend({
	init: function(opts) {
		this.docname = opts.docname;
		this._super(opts);
		//console.log("this ", this);
		//$.extend(this, opts);
		this.input_area = this.wrapper;
		//this.parent = this.wrapper;
		this.make_input();
		//this.show();
		//this.make_input();
		
	},
	make_input: function() {
		var me = this;
		this.$value = $('<div style="margin-top: 5px;">\
			<div class="text-ellipsis" style="display: inline-block; width: 90%;">\
				<i class="icon-paper-clip"></i> \
				<a class="attached-file" target="_blank"></a>\
			</div>\
			<a class="close">&times;</a></div>')
			.prependTo(me.input_area)
			.toggle(false);

		this.$value.find(".close").on("click", function() {
			if(me.frm) {
				me.frm.attachments.remove_attachment_by_filename(me.value, function() {
					me.parse_validate_and_set_in_model(null);
					me.set_input(null);
					me.refresh();
				});
			} else {
				me.dataurl = null;
				me.fileobj = null;
				me.set_input(null);
				me.refresh();
			}
		})
	},
	show: function(){
		if(!this.dialog) {
			this.dialog = new frappe.ui.Dialog({
				title: __(this.df.label || __("Upload")),
			});
		}

		$(this.dialog.body).empty();

		this.set_upload_options();
		jasper.upload.make(this.upload_options);
		this.dialog.show();
	},
	on_attach: function(){
		var me = this;
		//console.log("upload args ", this.args);
		var msgbox = msgprint(__("Uploading..."));
		this.args["method"] = "jasper_erpnext_report.utils.file.file_upload";
		return frappe.call({
			"method": "uploadfile",
			args: me.args,
			callback: function(r) {
				if(!r._server_messages)
					msgbox.hide();
				if(r.exc) {
					// if no onerror, assume callback will handle errors
					opts.onerror ? opts.onerror(r) : opts.callback(null, null, r);
					return;
				}
				var attachment = r.message;
				//opts.callback(attachment, r);
				$(document).trigger("upload_complete", attachment);
			}
		});
	},
	set_upload_options: function() {
		var me = this;
		this.upload_options = {
			parent: me.dialog.body,
			args: {},
			max_width: me.df.max_width,
			max_height: me.df.max_height,
			callback: function(attachment, r) {
				me.dialog.hide();
				me.on_upload_complete(attachment);
				me.set_input(attachment.file_url, this.dataurl);
				//me.set_model_value(attachment.file_url, "jasper_report_files", "Data");
			},
			onerror: function() {
				me.dialog.hide();
			},
		}

		if(this.frm) {
			console.log("this is form");
			this.upload_options.args = {
				//from_form: 1,
				doctype: me.frm.doctype,
				docname: me.frm.docname,
				method:  "jasper_erpnext_report.utils.file.file_upload"
			}
		};
		this.upload_options.on_attachs = function(args, dataurl) {
				me.dialog.hide();
				me.args = args;
				me.dataurl = dataurl;
				if(me.on_attach) {
					me.on_attach()
				}
				if(me.df.on_attach) {
					me.df.on_attach(args, dataurl);
				}
				me.on_upload_complete();
		}
	},
	on_upload_complete: function(attachment) {
		console.log("on_uploaad_complete ", this.doctype, this.docname, this.df.fieldname, this.df.fieldtype);
		if(this.frm) {
			this.parse_validate_and_set_in_model(attachment.file_url);
			this.refresh();
			this.frm.attachments.update_attachment(attachment);
		} else {
			this.set_input(attachment.file_url, this.dataurl);
			this.refresh();
		}
	},
	set_input: function(value, dataurl) {
			this.value = $.trim(value);
			if(this.value) {
			}
	},
	clear_input: function(){
		this.$value.toggle(true).find(".attached-file").empty();
	},
	get_value: function() {
			if(this.frm) {
				return this.value;
			} else {
				return this.fileobj ? (this.fileobj.filename + "," + this.dataurl) : null;
			}
	},
	set_model_value: function(value, fieldname, fieldtype) {
			if(frappe.model.set_value(this.doctype, this.docname, fieldname,
				value, fieldtype)) {
				this.last_value = value;
			}
	},
});


//jasper.dialog_upload_tree = Class.extend({
jasper.dialog_upload_tree =	frappe.ui.form.Control.extend({
	
	init: function(opts) {
		//$.extend(this, opts);
		this._super(opts);
		//this.docname = opts.docname;
		//this.input_area = this.wrapper;
		//console.log("opts ", opts);
		//this.make_input();
		this.maked = false;
	},
	make: function(){
		return;
	},
	make_wrapper: function() {
		return;
	},
	make_input: function() {
		var me = this;
		
		if(this.maked === false){
			//this.$value = $('<div id="jasper_upload_tree"></div>').prependTo(me.wrapper);
			this.value = this.$wrapper.html('<div id="jasper_upload_tree"></div>');
		/*this.$value.find(".close").on("click", function() {
			if(me.frm) {
				me.frm.attachments.remove_attachment_by_filename(me.value, function() {
					me.parse_validate_and_set_in_model(null);
					me.set_input(null);
					me.refresh();
				});
			} else {
				me.dataurl = null;
				me.fileobj = null;
				me.set_input(null);
				me.refresh();
			}
		});*/
		
			this.get_instance_tree();
			this.maked = true;
		};
		
		//var jsTree = $.jstree.create("#jasper_upload_tree");
		//console.log("jsTree ", jsTree);
		//var instance = $('#jasper_upload_tree').jstree(true);
		//var id = jsTree.create_node("#",{text:"teste1"});
		//console.log("instance ", instance.create_node);
		//$('#jasper_upload_tree').jstree("select_node", "1");
		//instance.deselect_all();
		//instance.select_node('1');
		//instance.create_node("#",{id:3, text:"teste1"});
		//console.log("other node ",instance.create_node("#",{id:3, text:"teste1"}));
		//$("#jasper_upload_tree").jstree('create_node', '#', {'id' : 'myId', 'text' : 'My Text'}, 'last');
		
		//jsTree.create_node(id,"teste1");
	},
	get_instance_tree: function(){
		var me = this;
		$('#jasper_upload_tree').jstree({
			'core' : {
			  'check_callback' : true,
			  'multiple' : false
			},
		    "types" : {
		       "default" : {
		         "icon" : "icon-paper-clip"
		       }
		     },
			"plugins" : ["state", "wholerow", "contextmenu", "types"],
			"contextmenu": {items: me.set_context()},
			
		});
		this.instance = $('#jasper_upload_tree').jstree(true);
	},
	show: function(){
		var me = this;
		this.make_input();
		//$('#jasper_upload_tree').jstree('create_node', '#', {'id' : '1944', 'text' : 'nosde1'}, 'last');
		//instance.delete_node(1);
		//$('#jasper_upload_tree').jstree("select_node", "1");
		//instance.create_node("#",{id:3, text:"teste1"});
		//$('#jasper_upload_tree').jstree("select_node", "1");
		if(!this.dialog) {
			this.dialog = new frappe.ui.Dialog({
				title: __(me.df.label || __("Upload")),
			});
		}

		$(this.dialog.body).empty();

		this.set_upload_options();
		jasper.upload.make(this.upload_options);
		this.dialog.show();
	},
	set_upload_options: function() {
		var me = this;
		this.selected = this.instance.get_selected();
		this.data = this.instance.get_node(this.selected).data;
		this.root = this.instance.get_node("#").children[0] || "#";
		//this.root = this.instance.get_node(this.instance.get_node("#").children[0]).data || "#";
		console.log("this is form ", this.root, this.selected, data.name);
		this.upload_options = {
			parent: me.dialog.body,
			args: {},
			max_width: me.df.max_width,
			max_height: me.df.max_height,
			callback: function(attachment, r) {
				me.dialog.hide();
				//instance.deselect_all();
				//selected = instance.get_selected();
				//var instance = $('#jasper_upload_tree').jstree(true);
				if (!r._server_messages){
					me.instance.create_node(me.selected.length > 0 ? me.selected[0]: me.root,{"id": attachment.name, "text":attachment.file_url,
					"data":{name: attachment.file_name.slice(0,-6)}});
				}
				me.on_upload_complete(attachment);
				//instance.create_node("1",{"id":2, "text":"teste2"});
				//instance.select_node(2);
				//me.set_input(attachment.file_url, this.dataurl);
				//me.set_model_value(attachment.file_url, "jasper_report_files", "Data");
			},
			onerror: function() {
				me.dialog.hide();
			},
		}

		if(this.frm) {
			this.upload_options.args = {
				//from_form: 1,
				parent_report: this.selected[0] || (this.root==="#"? "root":this.root),
				doctype: me.frm.doctype,
				docname: me.frm.docname,
				method:  "jasper_erpnext_report.utils.upload.file_upload"
			}
		};
		this.upload_options.on_attachs = function(args, dataurl) {
				me.dialog.hide();
				me.args = args;
				me.dataurl = dataurl;
				if(me.on_attach) {
					me.on_attach()
				}
				if(me.df.on_attach) {
					me.df.on_attach(args, dataurl);
				}
				me.on_upload_complete();
		}
	},
	on_upload_complete: function(attachment) {
		console.log("on_upload_complete ", this.doctype, this.docname, this.df.fieldname, this.df.fieldtype);
		if(this.frm) {
			this.parse_validate_and_set_in_model(attachment.file_url);
			this.refresh();
			this.frm.attachments.update_attachment(attachment);
			//this.set_model_value(value);
		} else {
			//this.set_input(attachment.file_url, this.dataurl);
			this.refresh();
		}
	},
	set_model_value: function(value) {
		if(frappe.model.set_value(this.doctype, this.docname, this.df.fieldname,
			value, this.df.fieldtype)) {
			this.last_value = value;
		}
	},
	set_input: function(name, file_name, url, parent_report) {
			if(url) {
				this.make_input();
				//var instance = $('#jasper_upload_tree').jstree(true);
				//instance.deselect_all();
				//selected = instance.get_selected();
				if (parent_report === "root")
					parent_report = null;
				console.log("set input instance ", name, parent_report);
				//this.instance.create_node(parent_report || "#",{"id": name, "text":url, "data":{name: attachment.file_name.slice(0,-6)}}});
				this.instance.create_node(parent_report || "#",{"id": name, "text":url, "data":{name: file_name.slice(0,-6)}});
			}
	},
	clear_input: function(){
		//this.$value.toggle(true).find(".attached-file").empty();
		//var instance = $('#jasper_upload_tree').jstree(true);
		//instance.get_container().empty();
		//instance.select_all();
		//console.log("seleted ", instance.get_selected());
		//instance.delete_node(instance.get_selected());
		//this.$value.find("#jasper_upload_tree").empty();
		//$('#jasper_upload_tree').jstree("init");
		$('#jasper_upload_tree').jstree("destroy").empty();
		$('#jasper_upload_tree').remove();
		//this.get_instance_tree();
		this.maked = false;
		//this.make_input();
	},
	set_context: function(){
		var me = this;
		return function(node) {
		    // The default set of all items
		    var items = {
		        /*renameItem: { // The "rename" menu item
		            label: "Rename",
		            action: function () {}
		        },*/
		        deleteItem: { // The "delete" menu item
		            label: "Delete",
		            action: function (d) {
						var inst = $.jstree.reference(d.reference);
	                    obj = inst.get_node(d.reference);
						console.log("was deleted ", obj, me);
						me.delete_item(obj);
						inst.delete_node(obj);
		            }
		        }
		    };

		    /*if ($(node).hasClass("folder")) {
		        // Delete the "delete" menu item
		        delete items.deleteItem;
				console.log("node has class folder");
		    }*/
			//delete items.deleteItem;
		    return items;
		};
	},
	delete_item: function(obj){
		var me = this;
		if(me.frm) {
			for (var i=0; i < obj.children.length; i++){
				var node = me.instance.get_node(obj.children[i]);
				me.frm.attachments.remove_attachment_by_filename(node.text, function() {
					me.parse_validate_and_set_in_model(null);
					//me.set_input(null);
					//me.refresh();
				});
			};
			me.frm.attachments.remove_attachment_by_filename(obj.text, function() {
				me.parse_validate_and_set_in_model(null);
				//me.set_input(null);
				//me.refresh();
			});
		} else {
			me.dataurl = null;
			me.fileobj = null;
			//me.set_input(null);
			//me.refresh();
		}
	}
});


jasper.upload = {
	make: function(opts) {
		if(!opts.args) opts.args = {};
		var $upload = $('<div class="file-upload">\
			<p class="small"><a class="action-attach disabled" href="#"><i class="icon-upload"></i> '
				+ __('Upload a file') + '</a></p>\
			<div class="action-attach-input">\
				<input class="alert alert-info" style="padding: 7px; margin: 7px 0px;" \
					type="file" name="filedata" />\
			</div>\
			<button class="btn btn-info btn-upload"><i class="icon-upload"></i> ' +__('Upload')
				+'</button></div>').appendTo(opts.parent);

		/*
				| <a class="action-link" href="#"><i class="icon-link"></i> '
				 + __('Attach as web link') + '</a>		
			<div class="action-link-input" style="display: none; margin-top: 7px;">\
				<input class="form-control" style="max-width: 300px;" type="text" name="file_url" />\
				<p class="text-muted">'
					+ (opts.sample_url || 'e.g. http://example.com/somefile.png') +
				'</p>\
			</div>\
		*/

		/*$upload.find(".action-link").click(function() {
			$upload.find(".action-attach").removeClass("disabled");
			$upload.find(".action-link").addClass("disabled");
			$upload.find(".action-attach-input").toggle(false);
			$upload.find(".action-link-input").toggle(true);
			$upload.find(".btn-upload").html('<i class="icon-link"></i> ' +__('Set Link'))
			return false;
		})*/

		$upload.find(".action-attach").click(function() {
			$upload.find(".action-link").removeClass("disabled");
			$upload.find(".action-attach").addClass("disabled");
			$upload.find(".action-link-input").toggle(false);
			$upload.find(".action-attach-input").toggle(true);
			$upload.find(".btn-upload").html('<i class="icon-upload"></i> ' +__('Upload'))
			return false;
		})

		// get the first file
		$upload.find(".btn-upload").click(function() {
			// convert functions to values
			for(key in opts.args) {
				if(typeof val==="function")
					opt.args[key] = opts.args[key]();
			}

			// add other inputs in the div as arguments
			opts.args.params = {};
			$upload.find("input[name]").each(function() {
				var key = $(this).attr("name");
				var type = $(this).attr("type");
				if(key!="filedata" && key!="file_url") {
					if(type === "checkbox") {
						opts.args.params[key] = $(this).is(":checked");
					} else {
						opts.args.params[key] = $(this).val();
					}
				}
			})

			//opts.args.file_url = $upload.find('[name="file_url"]').val();

			var fileobj = $upload.find(":file").get(0).files[0];
			jasper.upload.upload_file(fileobj, opts.args, opts);
		})
	},
	upload_file: function(fileobj, args, opts) {
		if(!fileobj && !args.file_url) {
			msgprint(__("Please attach a file"));
			return;
		}

		var dataurl = null;
		var _upload_file = function() {
			if(opts.on_attach) {
				opts.on_attach(args, dataurl)
			} else {
				var msgbox = msgprint(__("Uploading..."));
				return frappe.call({
					"method": "uploadfile",
					args: args,
					callback: function(r) {
						if(!r._server_messages)
							msgbox.hide();
						if(r.exc) {
							// if no onerror, assume callback will handle errors
							opts.onerror ? opts.onerror(r) : opts.callback(null, null, r);
							return;
						}
						var attachment = r.message;
						opts.callback(attachment, r);
						$(document).trigger("upload_complete", attachment);
					}
				});
			}
		}

		if(args.file_url) {
			_upload_file();
		} else {
			var freader = new FileReader();

			freader.onload = function() {
				args.filename = fileobj.name;
				if((opts.max_width || opts.max_height) && (/\.(gif|jpg|jpeg|tiff|png)$/i).test(args.filename)) {
					frappe.utils.resize_image(freader, function(_dataurl) {
						dataurl = _dataurl;
						args.filedata = _dataurl.split(",")[1];
						console.log("resized!");
						_upload_file();
					})
				} else {
					dataurl = freader.result;
					args.filedata = freader.result.split(",")[1];
					_upload_file();
				}
			};
			
			freader.readAsDataURL(fileobj);
		}
	}
}

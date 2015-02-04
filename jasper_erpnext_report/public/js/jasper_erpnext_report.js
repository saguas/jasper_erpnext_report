frappe.provide("jasper");

jasper.pending_reports = [];

jasper.poll_count = 0;

jasper.pages = {};

jasper_report_formats = {pdf:"icon-file-pdf", "docx": "icon-file-word", doc: "icon-file-word", xls:"icon-file-excel", xlsx:"icon-file-excel", 
						/*ppt:"icon-file-powerpoint", pptx:"icon-file-powerpoint",*/ odt: "icon-file-openoffice", ods: "icon-libreoffice",
	 					rtf:"fontello-icon-doc-text", submenu:"icon-grid"};

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

jasper.run_jasper_report = function(method, data, doc, type){
    //var format = format || 'pdf';
    //var args = 'path='+ encodeURIComponent(path) +'&format='+ format;
    var df = new $.Deferred();
    frappe.call({
	       "method": "jasper_erpnext_report.core.JasperWhitelist." + method,
	       args:{
               data: data,
	           docdata: doc,
               rtype: type
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
					   msgprint(msg[0].value, __("Report error! The report is taking too long... "));
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
    $banner = frappe.ui.toolbar.show_banner(__("Your report is ready to download! Click to ") + '<a class="download_report">download</a>')
    $banner.css({background: "lightGreen", opacity: 0.9});
	$banner.find(".download_report").click(function() {
        jasper.getReport(msg);
		jasper.close_banner($banner);
	});
};

jasper.getReport = function(msg){
    
    var reqIds = [];
    var expIds = [];
    for (var i =0; i<msg.length;i++){
        reqIds.push(msg[i].requestId);
        //assume reqids = expids
        if (msg[i].ids)
            expIds.push(msg[i].ids[0].id);
        else
            expIds.push("");
        
    };
    
    //var t = {reqId: reqIds, expId: expIds, fileName: msg[0].ids[0].fileName, reqtime: msg[0].reqtime, pformat: msg[0].pformat}
    //var reqdata = t;
	var reqdata = msg[0];
    console.log("this reqdata ", reqdata)
    
    var request = "/api/method/jasper_erpnext_report.core.JasperWhitelist.get_report?data="+encodeURIComponent(JSON.stringify(reqdata));
    console.log("request ", request)
    w = window.open(request);
	if(!w) {
		msgprint(__("Please enable pop-ups"));
	}
};

jasper.getList = function(page, doctype, docnames){
	var jpage = frappe.pages[page];
	if(jpage && jasper.pages[page]){
		list = jasper.pages[page];
		//console.log("exist lista ", list);
		setJasperDropDown(list, jasper.getOrphanReport);
	}else{
		method = "jasper_erpnext_report.core.JasperWhitelist.get_reports_list";
		data = {doctype: doctype, docnames: docnames};
		console.log("pedido for doctype %s docname %s ", doctype, docnames);
		jasper.jasper_make_request(method, data,function(response_data){
			console.log("resposta for doctype docname ", response_data, jpage, page);
			//frappe.pages[page]["jasper"] = response_data.message;
			jasper.pages[page] = response_data.message;
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
				if(typeof list[key] === "object"){
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
				console.log("jr_format ", jr_format, jr_name);
				//$(".nav.navbar-nav.navbar-right").popover({content:"teste content ", title:"popover jasper", placement:"left"});
				
				//$(ev.currentTarget).popover({content:"teste content ", title:"popover jasper", placement:"right"});
				//$(ev.currentTarget).popover('show');
				callback({jr_format: data.jr_format, jr_name: data.jr_name}, ev);
			};
			
			$(".nav.navbar-nav.navbar-right").append(html)
			//$(".nav.navbar-nav.navbar-right").prepend(html)
			$(".nav.navbar-nav.navbar-right .jrreports").on("click", clicked);
	};
		
};

jasper.check_for_ask_param = function(rname, callback){
    var robj = frappe.boot.jasper_reports_list[rname];
    if (robj === undefined){
        var page = jasper.get_page();
        robj = jasper.pages[page];
    }
    if (robj === undefined)
        return;

    var ret;
    if (robj.params && robj.params.length > 0){
        ret = jasper.make_dialog(robj, rname + " parameters", callback);
    }else{
        callback();
    }
    
    console.log("ret: ", ret);
};

jasper.make_menu = function(list, key, skey){
	//jasper_report_formats[list[key].formats[0]]
	var f = list[key].formats;
	//var t = list[key].formats.join(":");
	var icon_file = [];
	var html = "";
	for(var i=0; i < f.length; i++){
		var type = f[i];
		icon_file.push(repl('<i title="%(title)s" data-jr_format="%(f)s" data-jr_name="%(mykey)s" class="jasper-%(type)s"></i>', {title:key + " - " + type, mykey:key, f:f[i], type: jasper_report_formats[type]}));
	};
	//data-jr_format='+ t + ' data-jr_name="'+ key + '" class="jrreports"
	html = html + '<li>'
 	   + repl('<a class="jrreports" href="#" data-jr_format="%(f)s" data-jr_name="%(mykey)s"',{mykey:key, f:f[0]}) +' title="'+ key +' - pdf" >'+ icon_file.join(" ") + " " + skey  + '</a>' 
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
	var docnames;
	if (len > 1 && route[0] === "List"){
		var doctype = route[1];
		var page = [route[0], doctype].join("/");
		docnames = jasper.getCheckedNames(page);
		if (docnames.length === 0)
		{
			msgprint(__("Please, select at list one name"), __("Jasper Report"));
			return;
		};
	}else if(len > 2 && route[0] === "Form"){
		if (cur_frm){
			docnames = [cur_frm.doc.name];
		}else{
			msgprint(__("To print this doc you must be in a form."), __("Jasper Report"));
			return;
		}
	}
    var params;
    jasper.check_for_ask_param(data.jr_name, function(d){
    	console.log("docnames ", docnames);
    	var args = {fortype: "doctype", report_name: data.jr_name, doctype:"Jasper Reports", name_ids: docnames, pformat: data.jr_format, params: d};
    	var df = jasper.run_jasper_report("run_report", args, route[0], route[0]);
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
    var list = frappe.boot.jasper_reports_list;
	setJasperDropDown(list, function(data, ev){
		console.log("was clicked !! ", $(ev.target).data())
		jasper.getOrphanReport(data, ev);
	});
});

jasper.make_dialog = function(doc, title, callback){
	function ifyes(d){
		console.log("ifyes return ", d.get_values());
        if (callback){
            callback(d.get_values());
        }
	};
	function ifno(){
		console.log("ifno return ");
        if (callback){
            callback();
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
	var d = jasper.ask_dialog(title, doc.message, fields, ifyes, ifno);
	return d;
}

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



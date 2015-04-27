frappe.provide("jasper");



jasper.close_banner = function($banner){
    $banner.find(".close").click();
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

jasper.make_dialog = function(doc, title, callback){

    var fields = [];
	var params = doc.params;
	var docids = null;
	//Only one doctype_id field. Means, this parameters has the name (id) of open document (Form) or the ids of the selected documents in List view
	var is_doctype_id = false;

	for (var i=0; i < params.length; i++){
		var param = doc.params[i];
		if (param.is_copy === "Is doctype id"){
			is_doctype_id = true;
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
            callback({values: d.get_values(), abort: false, is_doctype_id: is_doctype_id});
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
};




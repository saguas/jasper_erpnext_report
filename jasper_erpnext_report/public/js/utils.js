frappe.provide("jasper");

jasper.pages = {};
jasper.report = {};


jasper.get_page = function(){
    var route = frappe.get_route();
	var doctype = route[1];
	var page = [route[0], doctype].join("/");
    return page;
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


jasper.shorten = function (text, maxLength) {
    var ret = text;
    if (ret.length > maxLength) {
        ret = ret.substr(0,maxLength-3) + "...";
    }
    return ret;
}

jasper.sortObject = function (o) {
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

jasper.getChecked = function(name){
	return $(frappe.pages[name]).find("input:checked");
};

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
};

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

jasper.get_country_from_alpha3 = function(lang){
	if (!jasper.CountryCode || jasper.CountryCode.length === 0)
		return;

	var country;

	for (var i=0; i<jasper.CountryCode.length;i++){
		if (jasper.CountryCode[i].code === lang){
			country = jasper.CountryCode[i].name;
			break;
		};
	};

	return country;
};


jasper.query_report_columns = function(){
    var columns = [];
    var cols = frappe.query_report.grid.getColumns();
    var len = cols.length;
    for(var i=0; i<len; i++){
        columns.push({name: cols[i].name, field: cols[i].field});
    }

    return columns;
};

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
};
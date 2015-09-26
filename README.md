
Jasper Erpnext Report
=============================
This project is a module to work with frappe framework **version 6.4.5 and above**. It integrate [JasperReports](http://community.jaspersoft.com/project/jasperreports-library) with frappe framework.
You can make your reports in [Jaspersoft Studio](http://community.jaspersoft.com/project/jaspersoft-studio) and import them in frappe with this module or send it to [JasperReports® Server](http://community.jaspersoft.com/project/jasperreports-server) and get it from there into the framework.
So you can use Jasper Erpnext Report in tree ways:

 - With JasperReports® Server mode - you need to install it.
 - Standalone mode.
 - Standalone and JasperReports® Server mode.

Any questions?

[![Join the chat at https://gitter.im/saguas/jasper_erpnext_report](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/saguas/jasper_erpnext_report?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

JasperReports® Server
=======
You make your reports in Jaspersoft Studio and put them in JasperReports Server. This way your reports are centralized. From Jasper Erpnext Report you get the reports that you want. After configure it you can send it to the JasperReports Server and get it back in pdf, docx,  xls, odds, dot and rtf. 

Standalone mode
==========
Here you don't need JasperReports Server. You make yours reports in Jaspersoft Studio and import them with Jasper Erpnext Report into frappe framework.
This module make the reports when asked to. In Standalone mode you can make more reports than in JasperReports Server mode.

How to Install
--------------

 1. Get Jasper Erpnext Report with `bench get-app jasper_erpnext_report https://github.com/saguas/jasper_erpnext_report.git`
 2.  Make sure you install **java jdk** - in ubuntu: `sudo apt-get install openjdk-7-jdk`.
 3.  Also you will need microsoft TrueType fonts (ttf-mscorefonts-installer) installed. In ubuntu - `sudo apt-get install ubuntu-restricted-extras` or `apt-apt install ttf-mscorefonts-installer` - you may need to uncomment multiverse in `/etc/apt/source.list`.
 4. Install in the framework with `bench install-app jasper_erpnext_report` 
 5. Install pyjnius with `bench update --requirements` 

How to use it?
==============

JasperReports® Server
---------------------
First, make a folder, in JasperReports® Server, to put the reports to use with this module - name it, for instance, erpnext.
Second, make your reports in Jaspersoft Studio and send them, from studio to the folder created in the first step, to JasperReports Server. 
![enter image description here](readmeimg/jasperserver_folder.png)

Now to import the folder (in my case is *`reports/`*) go to `Jasper Erpnext Report -> setup -> JasperServerConfig`. Once there make sure that *`Import All Reports`* is selected and make some configurations.

![enter image description here](readmeimg/jasperserverconfig.png)

After this you just have imported the settings of each report into the framework. That is all you need to make some decisions.

After that go to `Jasper Erpnext Report -> Jasper Reports` and configure each report as you plan when made it. See below how to configure reports.

Standalone mode
---------------

In this mode you just need to make the reports in Jaspersoft Studio. The simplest reports are made of one file with extension `jrxml` and some images and maybe some `localization_pt.properties` files. 
Then you need to import them into the framework. **See the `examples/` Folder**. The images must have, inside jrxml file, relative reference. So you must import them into Jaspersoft Studio when you are making your report - at the design time. Note that you still need to import them into the frappe framework after you finish the reports.
The localization files don't need to be imported if they are in `Java classpath`.

To import the report just go to `Jasper Erpnext Report -> Documents -> Jasper Reports` make a new report (you just need to give a name), select for `Choose Origin` **LocalServer** and before you can import the files that make your report you need to save the document. After save it an upload button appears. Note that after all files are imported you need to save again to make it permanent and to check if every thing is ok and all files needed were uploaded.
Again, you need to configure each doctype Jasper Reports document and then save them to take effect.
![enter image description here](readmeimg/jasper_new_report.png)

Report Configurations
---------------
**In Jasper Reports doctype configuration:**
(See the image above)

Only Administrator can configure reports.

You can make reports for General/Global purpose leaving Doctype and Report box empty.
You can also make reports for frappe doctype's or frappe report's choosing, respectively, Doctype or Report and select the correct document.
After this, you must choose in `Report for` box between Form, List, General and Server Hooks.

>**Form:** Choose this if the report has fields of some frappe Form/Doctype. This is the case when you want to make your custom report for, for instance, Quotation document.

>**List:** Choose this if you want to make some list, for instance, of Quotations.

>**General:** Choose this if you want that the report to be global and don't depend of any fields of any doctype.

>**Server Hooks:** Choose this if you want to give the ids from code.

**NOTE:** When you enter a document in Doctype or Report the jasper report (upper-right corner) only appears when you are in that document. 
If you leave it empty then it appears in upper-right corner of the desk.

The most common case, and the preferred way, when you make a jasper report is to automatically embed a querystring with a database select - In most cases Jaspersoft Studio make that for you.   
If you don't want or don't know how to make the database select then, in the case the report is for some doctype/Form or doctype/List, you can check `Use For Custom Fields` and the Jasper Report make
the select for you. This way is more time consuming than making the select to the database.

**Use For Custom Fields**

When you check `Use For Custom Fields` the Jasper Reports ignore any database select inside the `jrxml` file. 
You still has to indicate the fields in the xml field tag. The Jasperstudio make that automatically when you insert fields in the report in design mode.
When you use this option you can insert static fields from other doctype's in the report. For that name the field like this: doctype:docname:field. 
If you only use field for name then Jasper Reports will use the doctype you indicated and the docname you select inside that doctype.

**Email**

Check this if you allow to send the report by email.

**Don't Show report**

Check this if you don't want it to show in the upper-right corner.

**Use Virtualizer**

Because you may have a very large amount of data, the jasper print might be a very large file. This can lead to an Out Of Memory exception. 
Use Jasper Virtualizer in this case. Set in setup->JasperServerConfig the maximum number of report pages that will be stored in primary memory (RAM) before the sections of the report are store in virtual memory (DISK).

**Locale**

Choose the default language to use with this report. 

**Erpnext / Frappe Reports**

To make erpnext/frappe reports in Jasper Reports just choose the report in Report box and in the **jrxml file** indicate whitch fields do you want. 
The system will grab that fields and make the report. You can filter before tell Jasper Report to print. 

**Parameters:**

You can insert parameters inside your report `jrxml` file. Then you must tell the purpose of each parameter. 
For that you indicate in the `Type` box the type of the parameter.

>**Type:**

>**Is for copies:** If this parameter is for indicate in the document if is the Original, Duplicate or Triplicate.

>**Is for where clause:** If this parameter is for the where clause of the database select. The system will create a where clause with this parameter.

>**Is for page number:** It is not used at the moment.

>**Is for server hook:** It will call you function for you to return in code the value of the parameter.

>**Is doctype id:** The system will use this parameter in the where clause but don't create a where clause.

>**Other:** The system will ask for the value of the parameter to the user.


>**Report Number of Copies**

>You can make in one request at most tree copies of the report. One if you choose Original in `Report Number of Copies` box, Two for Duplicate and tree for Triplicate.
To take most advantage of this you must insert in your report a parameter and choose the type **Is for copies**.
  
>**Parameter Value**

>For any parameter you can pass a default value in this text box.

>**Database Sql Select:** 

>You can make any sql select to the database you want. 
>But at some point you will need to connect the report with erpnext/frappe. 
>For that you will tell, with parameters, what doctype or doctype's are you interested and more precisely, in that doctype, what document's you want.
>For doctype/Form and doctype/List the database sql select are very simples just make a sql select like this: select f1,f2,f3 from tabName $P!{param_name}. 
>Where f1,f2 and f3 are the name of the fields and tabName the name of some database table. 
>If you don't indicate the where clause the system will made it for you, in that case you must choose `Is for where clause`.
>That will be translated to select f1,f2,f3 from tabName where name in/not in (v1,v2,v3); Here name is the id for erpnext/frappe documents.  

>You can make a sql select with where clause, but you must choose `Is doctype id` for the parameter that will have the doctype id (name) of the document you choose to print.
>In this case you can provide only one id/name.

>You can make more exotic sql select's but you have, in the specific parameter, to choose `Is for server hook`.
>In this case you can return the where clause or an entire sql select.

> In the case you choose to return the entire sql select you must use $P!{param_name} for the value inside of the querystring tag of `jrxml` file.

> For more information see [Jasper Reports](http://jasperreports.sourceforge.net/sample.reference/query/).

**Hooks:**

`Report for` of type: **Server Hooks**

The system call for hook named `on_jasper_params_ids` with arguments `(data, params)`. 
`data` is the data that was sent from the client and `params` are the params attributes declared for the report.
You must check if this call is for the report you want with `data.report_name`. You can change everything in `data`.

This hook must return a dict with two fields: 

`{"ids": ["name_id1", "name_id2"], "report_type": "List/Form"}`

**data:**

	{
	fortype: fortype,// "doctype" or "query-report"
	
	report_name: data.jr_name,
	 
	doctype:"Jasper Reports",
	 
	cur_doctype: cur_doctype,
	 
	name_ids: docids, //ids (names) of the doctype's to make Jasper Reports
	
	pformat: jr_format, //pdf, etc.
	
	params: params, //this is object with param/value
	
	is_doctype_id: is_doctype_id,
	 
	grid_data: {columns: columns, data: grid_data}//this is for query-report's of erpnext and frappe
	}

**Parameters Hooks:**

The system call for hook named `on_jasper_params` with arguments `(data, params)`. 

Params is a list of `{"name":pname, 'value': pvalue, "attrs": param}`, where attrs is the param attributes.

	Some examples are:
	def on_jasper_params(self, data=None, params=None):
		a = []
		for param in params:
			if param.get("name") == "idade":
				a.append({"name": param.get("name"), "value": 35.6})
			else:
				#a.append({"name": param.get("name"), "value":['someusermail@gmail.com'], "param_type": "is for where clause"})
				a.append({"name": param.get("name"), "value":['someusermail@gmail.com']})
		
		#a.append({"name":param.get("name"), "value": ["Administrator", "someusermail@gmail.com"], "param_type": "is for where clause"})//here return where clause only
		#a.append({"name": params[0].get("name"), "value":'select name, email from tabUser where name in ("someusermail@gmail.com")'})//here return an entire sql select
		#a.append({"name": params[0].get("name"), "value":['Administrator', 'Guest'], "param_type": "is for where clause"})
		#a.append({"name": params[0].get("name"), "value":['Guest', 'Administrator']})
		#a.append({"name": params[0].get("name"), "value":345})

		return a

**Others Hooks**

The system call for hook named `jasper_before_run_report` with arguments `(data)` where `data` is the data that was sent from the client.

The system call for hook named `jasper_before_sendmail` with arguments `(data, file_name, output, url, doctype=doctype, name=name, content=content, 
subject=subject, sent_or_received=sent_or_received,
sender=sender, recipients=recipients, print_html=print_html, print_format=print_format, attachments=attachments,
send_me_a_copy=send_me_a_copy)`

The system call for hook named `jasper_after_sendmail` with arguments `(data, url, file_name, file_path)`

The system call for hook named `jasper_before_list_for_all` without arguments. Before get the list of all available reports. 

The system call for hook named `jasper_after_list_for_all` with arguments `(list)`. Argument is the list of all reports.

The system call for hook named `jasper_before_list_for_doctype` with arguments `(doctype, docnames, report)`. Before get the list of all reports for some doctype or report.

The system call for hook named `jasper_after_list_for_doctype` with arguments `(doctype, docnames, report, list)`. Last argument is the list of all reports for that doctype or report.

The system call for hook named `jasper_before_get_report` with arguments `(data)` where `data` is the data that was sent from the client.

The system call for hook named `jasper_after_get_report` with arguments `(file_name, content, url, filepath)`.


List of hooks:

`on_jasper_params`

`on_jasper_params_ids`

`jasper_before_run_report` 

`jasper_before_sendmail` and `jasper_after_sendmail`

`jasper_before_list_for_all` and `jasper_after_list_for_all`

`jasper_before_list_for_doctype` and `jasper_after_list_for_doctype

`jasper_before_get_report` and `jasper_after_get_report`


**Permission Rules:**

If you don't configure only Administrator or the authorized members in Permission Rules of Jaspe Reports can see and change the reports. 
You can tweak the Permission Rules of Jaspe Reports. 

Here you can choose who can access your report at the report level. This rules are combined with the rules of the frappe framework. 
In this way you can give doctype access to Jasper Reports in frappe, then here you can complement access at the report/document level.

You can remove this extra rules in `Jasper Erpnext Report>setup>JasperServerConfig` doctype unchecking `Ignore Jasper Permission Roles`.

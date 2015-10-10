frappe.provide("jasper");


jasper.dialog_upload = frappe.ui.form.ControlData.extend({
	init: function(opts) {
		this.docname = opts.docname;
		this._super(opts);
		this.input_area = this.wrapper;
		this.make_input();

	},
	make_input: function() {
		var me = this;
		this.$value = $('<div style="margin-top: 5px;">\
			<div class="text-ellipsis" style="display: inline-block; width: 90%;">\
				<i class="icon-paper-clip"></i>\
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
				title: __(this.df.label || "Upload"),
			});
		}

		$(this.dialog.body).empty();

		this.set_upload_options();
		jasper.upload.make(this.upload_options);
		this.dialog.show();
	},
	on_attach: function(){
		var me = this;
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
			},
			onerror: function() {
				me.dialog.hide();
			},
		}

		if(this.frm) {
			this.upload_options.args = {
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


jasper.dialog_upload_tree = frappe.ui.form.Control.extend({
	init: function(opts) {
		this._super(opts);
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
			this.value = this.$wrapper.html('<div id="jasper_upload_tree"></div>');

			this.get_instance_tree();
			this.maked = true;
		};

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
		if(!this.dialog) {
			this.dialog = new frappe.ui.Dialog({
				title: __(me.df.label || "Upload"),
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
		this.upload_options = {
			parent: me.dialog.body,
			args: {},
			max_width: me.df.max_width,
			max_height: me.df.max_height,
			callback: function(attachment, r) {
				me.dialog.hide();
				if (!r._server_messages){
					me.instance.create_node(me.selected.length > 0 ? me.selected[0]: me.root,{"id": attachment.name, "text":attachment.file_url,
					"data":{name: attachment.file_name.slice(0,-6)}});
				}
				me.on_upload_complete(attachment);
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
		if(this.frm) {
			this.parse_validate_and_set_in_model(attachment.file_url);
			this.refresh();
			this.frm.attachments.update_attachment(attachment);
		} else {
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
				if (parent_report === "root")
					parent_report = null;
				this.instance.create_node(parent_report || "#",{"id": name, "text":url, "data":{"name": file_name.split(".")[0]}});
			}
	},
	clear_input: function(){
		$('#jasper_upload_tree').jstree("destroy").empty();
		$('#jasper_upload_tree').remove();
		this.maked = false;
	},
	set_context: function(){
		var me = this;
		return function(node) {
		    // The default set of all items
		    var items = {
		        deleteItem: { // The "delete" menu item
		            label: "Delete",
		            action: function (d) {
						var inst = $.jstree.reference(d.reference);
	                    obj = inst.get_node(d.reference);
						me.delete_item(obj);
						inst.delete_node(obj);
		            }
		        }
		    };
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
				});
			};
			me.frm.attachments.remove_attachment_by_filename(obj.text, function() {
				me.parse_validate_and_set_in_model(null);
			});
		} else {
			me.dataurl = null;
			me.fileobj = null;
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

			var fileobj = $upload.find(":file").get(0).files[0];
			jasper.upload.upload_file(fileobj, opts.args, opts);
		})
	},
	upload_file: function(fileobj, args, opts) {
		if(!fileobj && !args.file_url) {
			msgprint(__("Please attach a file."));
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

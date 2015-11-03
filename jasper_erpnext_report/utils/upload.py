from __future__ import unicode_literals
__author__ = 'luissaguas'


import frappe
from frappe import _
from frappe.utils.file_manager import get_uploaded_content
from jasper_erpnext_report.utils.jasper_file_jrxml import write_file_jrxml
import mimetypes



def save_upload_file(fname, content, dn, parent=None):

	content_type = mimetypes.guess_type(fname)[0]
	file_data = write_file_jrxml(fname, content, dn=dn, content_type=content_type, parent=parent)

	return file_data

def save_uploaded(dn, parent):
	fname, content = get_uploaded_content()
	if content:
		return save_upload_file(fname, content, dn, parent=parent)
	else:
		raise Exception

"""
Function called to upload files from client
"""
def file_upload():
	#only administrator can upload reports!!
	comment = ""
	dt = frappe.form_dict.doctype
	dn = frappe.form_dict.docname
	parent = frappe.form_dict.parent_report
	filename = frappe.form_dict.filename

	if not filename:
		frappe.msgprint(_("Please select a file."),
			raise_exception=True)

	filedata = save_uploaded(dn, parent)

	if dt and dn:
		comment = frappe.get_doc(dt, dn).add_comment("Attachment",
			_("Added {0}").format("<a href='{file_url}' target='_blank'>{file_name}</a>".format(**filedata.as_dict())))

	return {
		"name": filedata.name,
		"file_name": filedata.file_name,
		"file_url": "".join(filedata.file_url.split("/files")[-1]),
		"parent_report": parent,
		"comment": comment.as_dict()
	}
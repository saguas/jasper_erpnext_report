from __future__ import unicode_literals
__author__ = 'luissaguas'


import frappe
from frappe import _
from frappe.utils.file_manager import get_uploaded_content, check_max_file_size, get_content_hash
from jasper_erpnext_report.utils.file import write_file_jrxml
import mimetypes


def save_upload_file(fname, content, dt, dn, parent=None):

	content_type = mimetypes.guess_type(fname)[0]
	file_size = check_max_file_size(content)
	file_data = write_file_jrxml(fname, content, content_type=content_type, parent=parent)
	content_hash = get_content_hash(file_data.pop("content"))

	file_data.update({
		"doctype": "File Data",
		"attached_to_report_name":parent,
		"attached_to_doctype": dt,
		"attached_to_name": dn,
		"file_size": file_size,
		"content_hash": content_hash,
	})

	f = frappe.get_doc(file_data)
	f.ignore_permissions = True
	try:
		f.insert()
	except frappe.DuplicateEntryError:
		return frappe.get_doc("File Data", f.duplicate_entry)
	return f

def save_uploaded(dt, dn, parent):
	fname, content = get_uploaded_content()
	if content:
		return save_upload_file(fname, content, dt, dn, parent)
	else:
		raise Exception

"""
Function called to upload files from client
"""
def file_upload():
	#only administrator can upload reports!!
	dt = frappe.form_dict.doctype
	dn = frappe.form_dict.docname
	parent = frappe.form_dict.parent_report
	filename = frappe.form_dict.filename

	if not filename:
		frappe.msgprint(_("Please select a file."),
			raise_exception=True)

	filedata = save_uploaded(dt, dn, parent)

	if dt and dn:
		comment = frappe.get_doc(dt, dn).add_comment("Attachment",
			_("Added {0}").format("<a href='{file_url}' target='_blank'>{file_name}</a>".format(**filedata.as_dict())))

	return {
		"name": filedata.name,
		"file_name": filedata.file_name,
		"file_url": filedata.file_url,
		"parent_report": parent,
		"comment": comment.as_dict()
	}
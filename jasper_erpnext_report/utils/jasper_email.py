from __future__ import unicode_literals
__author__ = 'luissaguas'

import frappe
from frappe import _
import json, os
from email.utils import formataddr

from jasper_erpnext_report.utils.file import get_jasper_path, write_file


def send_comm_email(d, file_name, output, fileid, sent_via=None, print_html=None, print_format=None, attachments='[]', send_me_a_copy=False):
	footer = None

	from frappe.core.doctype.communication.communication import get_email, attach_print, send, set_portal_link

	if sent_via:
		if hasattr(sent_via, "get_sender"):
			d.sender = sent_via.get_sender(d) or d.sender
		if hasattr(sent_via, "get_subject"):
			d.subject = sent_via.get_subject(d)
		if hasattr(sent_via, "get_content"):
			d.content = sent_via.get_content(d)

	if print_html:
		footer = "<hr>" + set_portal_link(frappe._dict({"doctype":"assets", "name": fileid}), d)

	mail = get_email(d.recipients, sender=d.sender, subject=d.subject,
		msg=d.content, footer=footer)

	if send_me_a_copy:
		mail.cc.append(frappe.db.get_value("User", frappe.session.user, "email"))

	if not print_html:
		mail.add_attachment(file_name, output, 'application/octet-stream')

	for a in json.loads(attachments):
		try:
			mail.attach_file(a)
		except IOError:
			frappe.throw(_("Unable to find attachment {0}").format(a))

	send(mail)


def sendmail(file_name, output, fileid, doctype=None, name=None, sender=None, content=None, subject=None, sent_or_received = "Sent", print_html=None, print_format=None, attachments='[]',
		 send_me_a_copy=False, recipients=None):

	sent_via = frappe.get_doc(doctype, name)
	d = frappe._dict({"subject": subject, "content": content, "sent_or_received": sent_or_received, "sender": sender or frappe.db.get_value("User", frappe.session.user, "email"),
	"recipients": recipients})
	send_comm_email(d, file_name, output, fileid, sent_via=sent_via, print_html=print_html, print_format=print_format, attachments=attachments, send_me_a_copy=send_me_a_copy)


def jasper_save_email(data, file_name, output, reqId, sender):

	sender = get_sender(sender)

	path_join = os.path.join
	rdoc = frappe.get_doc(data.get("doctype"), data.get('report_name'))
	for_all_sites = rdoc.jasper_all_sites_report
	jasper_path = get_jasper_path(for_all_sites)
	jasper_path_intern = path_join("jasper_sent_email", sender, reqId)
	outputPath = path_join(jasper_path, jasper_path_intern)
	frappe.create_folder(outputPath)
	file_path = path_join(outputPath, file_name)
	write_file(output, file_path, modes="wb")

	return file_path


def get_sender(sender):
	try:
		sender = json.loads(sender)
	except ValueError:
		pass

	if isinstance(sender, (tuple, list)) and len(sender)==2:
		sender = formataddr(sender)

	return sender
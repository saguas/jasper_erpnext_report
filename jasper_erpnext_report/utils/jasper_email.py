from __future__ import unicode_literals
__author__ = 'luissaguas'

import frappe
from frappe import _
import json, os
from email.utils import formataddr

from jasper_erpnext_report.utils.file import get_jasper_path, write_file, get_html_reports_path


def set_portal_link(sent_via, comm, endurl):
	"""set portal link in footer"""
	footer = ""

	if frappe.website.utils.is_signup_enabled():
		is_valid_recipient = frappe.utils.cstr(sent_via.get("email") or sent_via.get("email_id") or
			sent_via.get("contact_email")) in comm.recipients
		if is_valid_recipient:
			url = frappe.utils.quoted("%s/%s" % (frappe.utils.get_url(), endurl))
			footer = """<!-- Portal Link -->
					<p><a href="%s" target="_blank">View this on our website</a></p>""" % url

	return footer


def send_comm_email(d, file_name, output, sent_via=None, print_html=None, print_format=None, attachments='[]', send_me_a_copy=False):
	footer = None

	from frappe.core.doctype.communication.communication import get_email, send

	if sent_via:
		if hasattr(sent_via, "get_sender"):
			d.sender = sent_via.get_sender(d) or d.sender
		if hasattr(sent_via, "get_subject"):
			d.subject = sent_via.get_subject(d)
		if hasattr(sent_via, "get_content"):
			d.content = sent_via.get_content(d)

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
			frappe.throw(_("Unable to find attachment {0}.").format(a))

	send(mail)


def sendmail(file_name, output, fileid, doctype=None, name=None, sender=None, content=None, subject=None, sent_or_received="Sent", print_html=None, print_format=None, attachments='[]',
		send_me_a_copy=False, recipients=None):

	sent_via = frappe.get_doc(doctype, name)
	content += get_attach_link(fileid)
	d = frappe._dict({"subject": subject, "content": content, "sent_or_received": sent_or_received, "sender": sender or frappe.db.get_value("User", frappe.session.user, "email"),
	"recipients": recipients})
	send_comm_email(d, file_name, output, sent_via=sent_via, print_html=print_html, print_format=print_format, attachments=attachments, send_me_a_copy=send_me_a_copy)


def sendmail_v5(url, doctype=None, name=None, sender=None, content=None, subject=None, sent_or_received="Sent", send_email=False, print_html=None, print_format=None, attachments='[]',
		recipients=None):

	from frappe.core.doctype.communication.communication import make

	content += get_attach_link(url)
	return make(doctype=doctype, name=name, sender=sender, content=content, subject=subject, sent_or_received=sent_or_received, send_email=send_email, print_html=print_html, print_format=print_format, attachments=attachments,
		recipients=recipients)


def get_attach_link(url):
		"""Returns public link for the attachment via `templates/emails/print_link.html`."""
		return frappe.get_template("templates/emails/print_link.html").render({
			"url": "%s/%s" % (frappe.utils.get_url(), url)
		})


def get_email_pdf_path(report_name, reqId, site=None):

	site = site or frappe.local.site

	file_path = get_html_reports_path(report_name, where="reports", hash=reqId, localsite=site)

	return file_path


def get_email_other_path(data, file_name, reqId, sender):

	path_join = os.path.join
	rdoc = frappe.get_doc(data.get("doctype"), data.get('report_name'))
	for_all_sites = rdoc.jasper_all_sites_report
	jasper_path = get_jasper_path(for_all_sites)
	jasper_path_intern = path_join("jasper_sent_email", sender, reqId)
	outputPath = path_join(jasper_path, jasper_path_intern)
	frappe.create_folder(outputPath)
	file_path = path_join(outputPath, file_name)

	return file_path


def jasper_save_email(file_path, output):

	write_file(output, file_path, modes="wb")

	return file_path


def get_sender(sender):

	from jasper_erpnext_report.utils.utils import getFrappeVersion
	version = getFrappeVersion().major
	if version >= 5:
		if not sender and frappe.session.user != "Administrator":
			sender = frappe.utils.get_formatted_email(frappe.session.user)

		return sender

	try:
		sender = json.loads(sender)
	except ValueError:
		pass

	if isinstance(sender, (tuple, list)) and len(sender)==2:
		sender = formataddr(sender)

	return sender

def set_jasper_email_doctype(parent_name, sent_to, sender, when, filepath, filename):
	from frappe.model.naming import make_autoname

	jer_doc = frappe.new_doc('Jasper Email Report')

	jer_doc.jasper_email_report_name = parent_name
	jer_doc.name = make_autoname(parent_name + '/.DD./.MM./.YY./.#######')
	jer_doc.jasper_email_sent_to = sent_to
	jer_doc.jasper_email_sender = sender
	jer_doc.jasper_email_date = when
	jer_doc.jasper_file_name = filename
	jer_doc.jasper_report_path = filepath
	jer_doc.idx = frappe.utils.cint(frappe.db.sql("""select max(idx) from `tabJasper Email Report`""")[0][0]) + 1

	jer_doc.ignore_permissions = True
	jer_doc.insert()

	return jer_doc


def is_email_enabled():
	from frappe.email.smtp import _get_email_account
	acc = _get_email_account({"enable_outgoing": 1, "default_outgoing": 1})
	return acc != None
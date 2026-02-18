from email import message_from_string

import frappe
from frappe import _
from frappe.email.doctype.email_account.email_account import EmailAccount
from frappe.email.receive import InboundMail
from frappe.utils import cint
from frappe.utils.password import set_encrypted_password


class CustomEmailAccount(EmailAccount):
    @property
    def host(self):
        # Frappe EmailServer expects settings.host
        # Your Email Account stores it as email_server
        return self.get("host") or self.get("email_server")

    @host.setter
    def host(self, value):
        self.set("host", value)

    @property
    def incoming_port(self):
        # Keep stored port if present; otherwise derive a default
        port = self.get("incoming_port")
        if port:
            return cint(port)
        return 993 if cint(self.get("use_ssl")) else 143

    @incoming_port.setter
    def incoming_port(self, value):
        self.set("incoming_port", cint(value) if value is not None else value)

    @property
    def use_starttls(self):
        return cint(self.get("use_starttls"))

    @use_starttls.setter
    def use_starttls(self, value):
        self.set("use_starttls", cint(value))

    @property
    def use_ssl(self):
        return cint(self.get("use_ssl"))

    @use_ssl.setter
    def use_ssl(self, value):
        self.set("use_ssl", cint(value))

    @property
    def use_oauth(self):
        return cint(self.get("use_oauth"))

    @use_oauth.setter
    def use_oauth(self, value):
        self.set("use_oauth", cint(value))

    @property
    def username(self):
        return self.get("username") or self.get("login_id") or self.get("email_id")

    @property
    def password(self):
        return self.get_password("password")

    def set_password(self, fieldname, password):
        set_encrypted_password(self.doctype, self.name, password, fieldname=fieldname)

    def get_inbound_mails(self) -> list[InboundMail]:
        """retrive and return inbound mails."""
        mails = []

        def process_mail(messages, append_to=None):
            for index, message in enumerate(messages.get("latest_messages", [])):
                try:
                    _msg = message_from_string(
                        message.decode("utf-8", errors="replace")
                    )

                    # Important: If the email is auto-generated, we do not create a ticket
                    if _msg.get("X-Auto-Generated"):
                        continue

                    uid = (
                        messages["uid_list"][index]
                        if messages.get("uid_list")
                        else None
                    )
                    seen_status = messages.get("seen_status", {}).get(uid)
                    if self.email_sync_option != "UNSEEN" or seen_status != "SEEN":
                        _inbound_mail = InboundMail(
                            message,
                            self,
                            frappe.safe_decode(uid),
                            seen_status,
                            append_to,
                        )
                        mails.append(_inbound_mail)
                except Exception as e:
                    # Log the error but continue processing other emails
                    frappe.log_error(
                        title=_(
                            "Error processing email at index {0}, message: {1}"
                        ).format(index, e),
                        message=frappe.get_traceback(),
                    )
                    self.handle_bad_emails(index, message, frappe.get_traceback())
                    continue

        if not self.enable_incoming:
            return []

        try:
            if self.service == "Frappe Mail":
                frappe_mail_client = self.get_frappe_mail_client()
                messages = frappe_mail_client.pull_raw(
                    last_received_at=self.last_synced_at
                )
                process_mail(messages)
                self.db_set(
                    "last_synced_at", messages["last_received_at"], update_modified=False
                )
            else:
                email_sync_rule = self.build_email_sync_rule()
                email_server = self.get_incoming_server(
                    in_receive=True, email_sync_rule=email_sync_rule
                )
                if self.use_imap:
                    # process all given imap folder
                    for folder in self.imap_folder:
                        if email_server.select_imap_folder(folder.folder_name):
                            email_server.settings["uid_validity"] = folder.uidvalidity
                            messages = (
                                email_server.get_messages(
                                    folder=f'"{folder.folder_name}"'
                                )
                                or {}
                            )
                            process_mail(messages, folder.append_to)
                else:
                    # process the pop3 account
                    messages = email_server.get_messages() or {}
                    process_mail(messages)

                # close connection to mailserver
                email_server.logout()
        except Exception:
            self.log_error(
                title=_("Error while connecting to email account {0}").format(self.name)
            )
            return []

        return mails

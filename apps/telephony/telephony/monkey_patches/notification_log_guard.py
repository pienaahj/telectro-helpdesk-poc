# telephony/monkey_patches/notification_log_guard.py
import frappe

def snap_ticket_seq_state():
    import frappe
    max_ticket = frappe.db.sql("SELECT MAX(name) FROM `tabHD Ticket`")[0][0]
    seq_next   = frappe.db.sql("SELECT next_not_cached_value FROM `hd_ticket_id_seq`")[0][0]
    return {
        "max_ticket": int(max_ticket or 0),
        "seq_next": int(seq_next or 0),
        "gap": int(seq_next - ((max_ticket or 0) + 1)),
        "max_exists": bool(frappe.db.exists("HD Ticket", str(max_ticket))) if max_ticket else False,
    }


def apply():
    """
    Guard Notification Log email sending so email failures do NOT abort the
    transaction that created the Notification Log (and indirectly your HD Ticket).

    site_config.json toggles:
      - telephony_guard_notification_email: true/false (default true)
      - telephony_guard_notification_email_debug: true/false (default false)
    """
    if not frappe.conf.get("telephony_guard_notification_email", True):
        return

    if getattr(frappe.flags, "telephony_notification_guard_applied", False):
        return

    try:
        from frappe.desk.doctype.notification_log import notification_log as nl
    except Exception:
        return

    orig = getattr(nl, "send_notification_email", None)
    if not orig:
        return

    if getattr(orig, "__telephony_guard_wrapped__", False):
        frappe.flags.telephony_notification_guard_applied = True
        return

    def guarded_send_notification_email(doc, *args, **kwargs):
        try:
            return orig(doc, *args, **kwargs)
        except Exception as e:
            # Never rollback the transaction because notification email failed.
            # Log for visibility.
            try:
                logger = frappe.logger("telephony")
                docname = getattr(doc, "name", None)
                logger.warning(
                    "Notification email suppressed for Notification Log %s: %s",
                    docname,
                    repr(e),
                    exc_info=True,
                )
            except Exception:
                pass

            if frappe.conf.get("telephony_guard_notification_email_debug"):
                print(
                    f"[telephony] notification email suppressed for Notification Log {getattr(doc, 'name', None)}: {repr(e)}"
                )

            return None

    guarded_send_notification_email.__telephony_guard_wrapped__ = True
    nl.send_notification_email = guarded_send_notification_email

    frappe.flags.telephony_notification_guard_applied = True

    if frappe.conf.get("telephony_guard_notification_email_debug"):
        print("[telephony] notification_log_guard applied")

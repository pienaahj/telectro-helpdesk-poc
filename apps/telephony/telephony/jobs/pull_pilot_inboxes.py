import frappe

# Bump this any time you change logic so you can confirm the scheduler is running the new code.
JOB_FINGERPRINT = "2026-02-18TDEBUG-02"

BASE = "telephony:pull_pilot_inboxes"

ACCOUNTS = ["Faults", "Routing", "PABX", "Helpdesk"]

# --- mail identity helpers (best-effort across Frappe versions) ---

def _mail_uid(m):
    return getattr(m, "uid", None)

def _mail_message_id(m):
    return getattr(m, "message_id", None) or getattr(m, "msgid", None)

def _mail_from(m):
    return getattr(m, "from_email", None) or getattr(m, "sender", None) or getattr(m, "from_", None)

def _mail_subject(m):
    return getattr(m, "subject", None)

def _mail_identity(m):
    return {
        "uid": _mail_uid(m),
        "message_id": _mail_message_id(m),
        "from": _mail_from(m),
        "subject": _mail_subject(m),
    }

def _set(key, val):
    frappe.cache().set_value(f"{BASE}:{key}", val)

def _get(key):
    return frappe.cache().get_value(f"{BASE}:{key}")

def run():
    last_mail_meta = None
    # --- breadcrumbs ---
    _set("fingerprint", JOB_FINGERPRINT)
    _set("last_run", str(frappe.utils.now_datetime()))
    _set("stage", "start")
    _set("last_err", None)

    # --- lock (RedisWrapper supports .lock()) ---
    lock_key = f"{BASE}:lock"
    lock = frappe.cache().lock(lock_key, timeout=55, blocking_timeout=1)
    acquired = lock.acquire(blocking=False)
    _set("lock_acquired", 1 if acquired else 0)
    if not acquired:
        _set("last_skip", str(frappe.utils.now_datetime()))
        _set("stage", "skipped")
        return
    # ✅ only when lock acquired:
    _set("last_start", str(frappe.utils.now_datetime()))

    try:
        total = 0
        per = {}

        for acct_name in ACCOUNTS:
            _set("stage", f"acct:{acct_name}:start")
            uids = []
            try:
                acc = frappe.get_doc("Email Account", acct_name)
                if not acc.enable_incoming:
                    per[acct_name] = {"disabled": True, "mails": 0, "processed": 0}
                    continue

                # Pull + process ourselves so we can count + capture last Communication
                mails = acc.get_inbound_mails() or []
                processed = 0
                last_comm = None
                last_ticket = None

                for m in mails:
                    # process() returns a Communication doc (or docname depending on version)
                    comm = m.process()
                    meta = _mail_identity(m)
                    last_mail_meta = {"acct": acct_name, **meta}
                    uid = meta.get("uid")
                    if uid is not None:
                        try:
                            uids.append(int(uid))
                        except Exception:
                            pass
                    processed += 1
                    last_comm = getattr(comm, "name", comm)

                    # Try to fetch reference (HD Ticket) if it exists
                    try:
                        cdoc = frappe.get_doc("Communication", last_comm)
                        if cdoc.reference_doctype == "HD Ticket":
                            last_ticket = cdoc.reference_name
                    except Exception:
                        pass

                frappe.db.commit()

                entry = {"disabled": False, "mails": len(mails), "processed": processed}
                if uids:
                    entry.update({"uid_min": min(uids), "uid_max": max(uids)})
                per[acct_name] = entry
                total += processed

                # Update global "last_*" based on most recent processed mail
                if last_comm:
                    _set("last_comm", last_comm)
                if last_ticket:
                    _set("last_ticket", last_ticket)

                _set("stage", f"acct:{acct_name}:done")

            except Exception as e:
                frappe.db.rollback()
                per[acct_name] = {"error": repr(e)[:500]}
                # keep going with other accounts, but remember the last error
                _set("last_err", f"{acct_name}: {repr(e)[:500]}")
                _set("stage", f"acct:{acct_name}:error")

        if last_mail_meta:
            _set("last_mail_meta", last_mail_meta)
        _set("processed_total", total)
        _set("processed_last_run", total)
        _set("per_account", per)
        _set("last_ok", str(frappe.utils.now_datetime()))
        _set("stage", "done")

    except Exception as e:
        frappe.db.rollback()
        _set("last_err", repr(e)[:1000])
        _set("stage", "fatal")
        raise

    finally:
        try:
            lock.release()
        except Exception:
            pass

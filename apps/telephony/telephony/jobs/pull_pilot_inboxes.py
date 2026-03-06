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

DEDUPE_TTL_SECONDS = 6 * 3600  # 6 hours

SUBJECT_BLOCK_CONTAINS = [
    "assigned a new task",
    "undelivered mail returned to sender",
]

SENDER_BLOCK_PREFIXES = [
    "mailer-daemon",
    "postmaster",
]

def _dedupe_key(acct: str, ident: str) -> str:
    return f"{BASE}:dedupe:{acct}:{ident}"

def _dedupe_seen(acct: str, ident: str) -> bool:
    if not ident:
        return False
    return frappe.cache().get_value(_dedupe_key(acct, ident)) is not None

def _dedupe_mark(acct: str, ident: str) -> None:
    if not ident:
        return
    try:
        frappe.cache().set_value(_dedupe_key(acct, ident), 1, expires_in_sec=DEDUPE_TTL_SECONDS)
    except TypeError:
        frappe.cache().set_value(_dedupe_key(acct, ident), 1)

def _is_blocked_meta(meta: dict) -> bool:
    subj = (meta.get("subject") or "").lower()
    frm = (meta.get("from") or "").lower()
    if any(x in subj for x in SUBJECT_BLOCK_CONTAINS):
        return True
    if any(frm.startswith(p) for p in SENDER_BLOCK_PREFIXES):
        return True
    return False

def _dedupe_ident(meta: dict) -> str:
    # Prefer UID; fall back to Message-ID
    uid = meta.get("uid")
    if uid:
        return f"uid:{uid}"
    mid = meta.get("message_id")
    if mid:
        return f"mid:{mid}"
    return ""

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
                skipped_blocked = 0
                skipped_dedupe = 0
                processed = 0
                last_comm = None
                last_ticket = None

                # counters at account scope (define these before the loop)
                # skipped_blocked = 0
                # skipped_dedupe = 0

                for m in mails:
                    meta = _mail_identity(m)
                    ident = _dedupe_ident(meta)

                    if _is_blocked_meta(meta):
                        skipped_blocked += 1
                        _set("last_skip_meta", {"acct": acct_name, "reason": "blocked", **meta})
                        continue

                    if ident and _dedupe_seen(acct_name, ident):
                        skipped_dedupe += 1
                        _set("last_skip_meta", {"acct": acct_name, "reason": "dedupe", **meta})
                        continue

                    # --- process the mail (this is your existing behavior) ---
                    try:
                        comm = m.process()
                        processed += 1
                        last_comm = getattr(comm, "name", comm)

                        if ident:
                            _dedupe_mark(acct_name, ident)

                        try:
                            cdoc = frappe.get_doc("Communication", last_comm)
                            if cdoc.reference_doctype == "HD Ticket":
                                last_ticket = cdoc.reference_name
                        except Exception:
                            pass

                        last_mail_meta = {"acct": acct_name, **meta}
                        uid = meta.get("uid")
                        if uid is not None:
                            try:
                                uids.append(int(uid))
                            except Exception:
                                pass

                        frappe.db.commit()  # ✅ commit each successful mail
                    except Exception as e:
                        frappe.db.rollback()
                        _set("last_err", f"{acct_name}: {repr(e)[:200]}")
                        # continue with next mail
                        continue

                entry = {
                    "disabled": False,
                    "mails": len(mails),
                    "processed": processed,
                    "skipped_blocked": skipped_blocked,
                    "skipped_dedupe": skipped_dedupe,
                }
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

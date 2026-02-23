import re
import frappe
import hashlib

# --- Parsing helpers ---------------------------------------------------------

_SITE_RE  = re.compile(r"(?i)\bSITE\s*:\s*([^\r\n]+)")
_ASSET_RE = re.compile(r"(?i)\bASSET\s*:\s*([^\r\n]+)")

def _bounce_guard_key(sender: str, subject: str) -> str:
    s = (sender or "").strip().lower()
    subj = (subject or "").strip().lower()
    raw = f"{s}|{subj}"
    h = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
    return f"telephony:bounce:seen:{h}"

def _bounce_reason(sender: str, subject: str) -> str | None:
    sender = (sender or "").strip().lower()
    subject = (subject or "").strip()

    # sender prefix denylist
    prefixes = _conf_list("telephony_autoreply_sender_block_prefixes", ["mailer-daemon", "postmaster"])
    for p in prefixes:
        p = (p or "").strip().lower()
        if p and sender.startswith(p + "@"):
            return f"sender_blocked:{p}"

    # subject contains denylist
    needles = _conf_list("telephony_autoreply_subject_block_contains", ["Undelivered Mail Returned to Sender"])
    s = subject.lower()
    for n in needles:
        n = (n or "").strip()
        if n and n.lower() in s:
            return f"subject_blocked:{n}"

    return None

def _conf_int(key: str, default: int) -> int:
    try:
        v = frappe.conf.get(key)
    except Exception:
        v = None
    if v is None:
        return default
    try:
        return int(v)
    except Exception:
        return default

def _dedupe_key_secondary(ticket_id: str, to_email: str, confirm_link: str) -> str:
    ticket_id = (ticket_id or "").strip()
    to_email = (to_email or "").strip().lower()
    confirm_link = (confirm_link or "").strip()
    raw = f"{ticket_id}|{to_email}|{confirm_link}"
    h = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
    return f"telephony:autoreply:sent2:{ticket_id}:{h}"

def _cache_set_with_ttl(cache, key: str, value: str, ttl_seconds: int):
    # Works on modern Frappe; if TTL isn't supported, it will still set value (no TTL).
    try:
        cache.set_value(key, value, expires_in_sec=ttl_seconds)
    except TypeError:
        cache.set_value(key, value)

def _first_match(pattern: re.Pattern, text: str) -> str | None:
    if not text:
        return None
    m = pattern.search(text)
    if not m:
        return None
    val = (m.group(1) or "").strip()
    return val or None

def _text_from_ticket(doc) -> str:
    parts = []
    for key in ("subject", "description"):
        v = doc.get(key)
        if v:
            parts.append(str(v))
    return "\n".join(parts)

def _sender_email(doc) -> str | None:
    # Common fields across Helpdesk stacks
    for key in ("raised_by", "contact_email", "sender", "email_from"):
        v = doc.get(key)
        if v and "@" in str(v):
            return str(v).strip().lower()
    return None

# --- Customer lookup ---------------------------------------------------------

def _customer_from_sender(email: str) -> tuple[str | None, str]:
    """
    Map sender email -> Customer with a reason code.

    Returns:
      (customer_name or None, reason_code)

    Reason codes:
      - empty_email
      - contact_email_id_match
      - contact_email_child_match
      - no_contact_match
      - no_dynamic_link
      - no_customer_link
      - multiple_customer_links
      - customer_direct_match_email_id
      - customer_direct_match_email
      - no_match
    """
    email = (email or "").strip().lower()
    if not email:
        return None, "empty_email"

    contact = None
    contact_reason = None

    # 1) Contact.email_id
    if frappe.db.exists("DocType", "Contact"):
        contact = frappe.db.get_value("Contact", {"email_id": email}, "name")
        if contact:
            contact_reason = "contact_email_id_match"

    # 2) Contact Email child table
    if not contact and frappe.db.exists("DocType", "Contact Email"):
        contact = frappe.db.get_value("Contact Email", {"email_id": email}, "parent")
        if contact:
            contact_reason = "contact_email_child_match"

    if contact:
        if not frappe.db.exists("DocType", "Dynamic Link"):
            return None, "no_dynamic_link"

        links = frappe.get_all(
            "Dynamic Link",
            filters={"parenttype": "Contact", "parent": contact, "link_doctype": "Customer"},
            pluck="link_name",
            limit_page_length=2,
            ignore_permissions=True,
        )

        if len(links) == 1 and links[0]:
            return links[0], contact_reason or "customer_linked"

        if len(links) > 1:
            return None, "multiple_customer_links"

        return None, "no_customer_link"

    # 3) Customer direct
    if frappe.db.exists("DocType", "Customer"):
        try:
            meta = frappe.get_meta("Customer")
            fields = {df.fieldname for df in meta.fields}
        except Exception:
            fields = set()

        if "email_id" in fields:
            cust = frappe.db.get_value("Customer", {"email_id": email}, "name")
            if cust:
                return cust, "customer_direct_match_email_id"

        if "email" in fields:
            cust = frappe.db.get_value("Customer", {"email": email}, "name")
            if cust:
                return cust, "customer_direct_match_email"

    return None, "no_match"

# --- Location lookup ---------------------------------------------------------

def _location_from_site_label(site_label: str) -> str | None:
    """
    Map site label to Location.
    Try:
      - name exact
      - location_name exact (if exists)
      - begins-with fallback
    """
    site_label = (site_label or "").strip()
    if not site_label:
        return None

    if not frappe.db.exists("DocType", "Location"):
        return None

    # Exact name
    if frappe.db.exists("Location", site_label):
        return site_label

    # location_name exact (field may exist depending on version)
    if frappe.db.has_column("Location", "location_name"):
        loc = frappe.db.get_value("Location", {"location_name": site_label}, "name")
        if loc:
            return loc

    # Soft fallback: startswith on name or location_name
    # (Pilot-friendly; keep it conservative)
    candidates = []
    try:
        candidates = frappe.get_all(
            "Location",
            or_filters=(
                [{"name": ["like", site_label + "%"]}]
                + ([{"location_name": ["like", site_label + "%"]}] if frappe.db.has_column("Location", "location_name") else [])
            ),
            pluck="name",
            limit_page_length=5,
            ignore_permissions=True,
        )
    except Exception:
        candidates = []

    return candidates[0] if candidates else None

# --- Hook -------------------------------------------------------------------

def populate_from_email(doc, method=None):
    """
    Stage A intake:
      - map sender -> custom_customer
      - parse SITE: -> custom_site
      - parse ASSET: -> custom_equipment_ref
    Only fill when empty (never overwrite user input).
    """
    # Only act on new docs
    if getattr(doc, "is_new", None) and not doc.is_new():
        return

    # 1) Customer from sender email
    if not doc.get("custom_customer"):
        sender = _sender_email(doc)
        if sender:
            try:
                cust, _reason = _customer_from_sender(sender)
                if cust:
                    doc.set("custom_customer", cust)
            except Exception:
                cust = None
            if cust:
                doc.set("custom_customer", cust)


    # 2) Parse structured tags from subject+description
    text = _text_from_ticket(doc)

    if not doc.get("custom_site"):
        site_label = _first_match(_SITE_RE, text)
        if site_label:
            loc = _location_from_site_label(site_label)
            if loc:
                doc.set("custom_site", loc)

    if not doc.get("custom_equipment_ref"):
        asset = _first_match(_ASSET_RE, text)
        if asset:
            doc.set("custom_equipment_ref", asset[:140])

def _comm_text(comm) -> str:
    # Prefer text_content (already plain), fall back to content
    txt = comm.get("text_content") or comm.get("content") or ""
    return str(txt)

def _resolve_site_to_location(site_label: str) -> str | None:
    """
    Resolve SITE label to Location.
    Pilot-friendly: prefer exact match under "Pilot Sites" (if that exists),
    then global exact match, then conservative startswith.
    """
    site_label = (site_label or "").strip()
    if not site_label or not frappe.db.exists("DocType", "Location"):
        return None

    # If pilot root exists, constrain to it first
    pilot_root = "Pilot Sites" if frappe.db.exists("Location", "Pilot Sites") else None

    def _find(filters):
        return frappe.db.get_value("Location", filters, "name")

    # 1) exact by name
    if frappe.db.exists("Location", site_label):
        if not pilot_root:
            return site_label
        # if pilot_root exists, only accept if it's under pilot tree (best effort)
        parent = frappe.db.get_value("Location", site_label, "parent_location")
        if parent == pilot_root or site_label == pilot_root:
            return site_label

    # 2) exact by location_name (if field exists)
    if frappe.db.has_column("Location", "location_name"):
        filters = {"location_name": site_label}
        if pilot_root:
            filters["parent_location"] = pilot_root
        loc = _find(filters)
        if loc:
            return loc

    # 3) startswith fallback (conservative)
    or_filters = [{"name": ["like", site_label + "%"]}]
    if frappe.db.has_column("Location", "location_name"):
        or_filters.append({"location_name": ["like", site_label + "%"]})

    filters = {}
    if pilot_root:
        filters["parent_location"] = pilot_root

    try:
        rows = frappe.get_all(
            "Location",
            filters=filters,
            or_filters=or_filters,
            pluck="name",
            limit_page_length=5,
            ignore_permissions=True,
        )
        return rows[0] if rows else None
    except Exception:
        return None

def populate_ticket_from_communication(comm, method=None):
    """
    Stage A v2:
      Communication(Received) -> parse SITE/ASSET -> write onto referenced HD Ticket.
    """
    try:
        if not comm:
            return

        # Only inbound mail
        sor = (comm.get("sent_or_received") or "").strip().lower()
        if sor and sor != "received":
            return

        if comm.get("reference_doctype") != "HD Ticket":
            return

        ticket_id = comm.get("reference_name")
        if not ticket_id:
            return

        cache = frappe.cache()

        # Get current ticket values (avoid full save)
        tvals = frappe.db.get_value(
            "HD Ticket",
            ticket_id,
            ["custom_site", "custom_equipment_ref", "custom_customer", "email_account"],
            as_dict=True,
        )
        if not tvals:
            return
        
        # H1: Auto-close bounce/system tickets
        sender = (comm.get("sender") or "").strip().lower()
        subject = (comm.get("subject") or "").strip()
        reason = _bounce_reason(sender, subject)

        # J3: keep a "last non-bounce sender" breadcrumb so mailer-daemon doesn't dominate dashboards
        if not reason:
            cache.set_value("telephony:stage_a:last_sender_non_bounce", sender or "")
            cache.set_value("telephony:stage_a:last_sender_non_bounce_ticket", ticket_id)
            cache.set_value("telephony:stage_a:last_sender_non_bounce_subject", (subject or "")[:140])
            cache.set_value("telephony:stage_a:last_sender_non_bounce_at", str(frappe.utils.now_datetime()))
            
        if reason:
            # J1: bounce guard window (rate-limit repeated bounces)
            if _conf_bool("telephony_bounce_guard_enabled", 1):
                window = max(60, _conf_int("telephony_bounce_guard_window_seconds", 3600))
                gk = _bounce_guard_key(sender, subject)
                seen_at = cache.get_value(gk)

                if seen_at is not None:
                    cache.set_value("telephony:stage_a:last_bounce_guard_hit", "1")
                    cache.set_value("telephony:stage_a:last_bounce_guard_seen_at", str(seen_at))
                else:
                    _cache_set_with_ttl(cache, gk, str(frappe.utils.now_datetime()), window)
                    cache.set_value("telephony:stage_a:last_bounce_guard_hit", "0")
                    cache.set_value("telephony:stage_a:last_bounce_guard_seen_at", "")

                cache.set_value("telephony:stage_a:last_bounce_guard_key", gk)
                cache.set_value("telephony:stage_a:last_bounce_guard_window_seconds", str(window))
            
            # close ticket        
            frappe.db.set_value("HD Ticket", ticket_id, {"status": "Closed"}, update_modified=False)

            # set bounce breadcrumbs
            cache.set_value("telephony:stage_a:last_bounce_ticket", ticket_id)
            cache.set_value("telephony:stage_a:last_bounce_reason", reason)
            cache.set_value("telephony:stage_a:last_bounce_subject", subject[:140])
            cache.set_value("telephony:stage_a:last_bounce_sender", sender[:140])
            cache.set_value("telephony:stage_a:last_bounce_at", str(frappe.utils.now_datetime()))

            return

        text = _comm_text(comm)

        # Parse tags from comm text
        site_label = _first_match(_SITE_RE, text)
        asset = _first_match(_ASSET_RE, text)

        updates = {}

        # only set if empty
        if not (tvals.get("custom_site") or "") and site_label:
            loc = _resolve_site_to_location(site_label)
            if loc:
                updates["custom_site"] = loc

        if not (tvals.get("custom_equipment_ref") or "") and asset:
            updates["custom_equipment_ref"] = asset[:140]

        # Optional: customer mapping from sender email
        if not (tvals.get("custom_customer") or ""):
            sender = (comm.get("sender") or "").strip().lower()

            # Customer mapping breadcrumbs (interim story)
            cache.set_value("telephony:stage_a:last_sender", sender or "")

            cust = None
            reason = "attempt_lookup"
            try:
                cust, reason = _customer_from_sender(sender)
            except Exception:
                cust, reason = None, "lookup_error"

            if cust:
                updates["custom_customer"] = cust
                # keep reason from helper (already precise)
            else:
                # reason already describes why
                pass

            cache.set_value("telephony:stage_a:last_custom_customer", cust or "")
            cache.set_value("telephony:stage_a:last_customer_map_reason", reason)

        if updates:
            frappe.db.set_value("HD Ticket", ticket_id, updates, update_modified=False)

            cache.set_value("telephony:stage_a:last_ticket", ticket_id)
            cache.set_value("telephony:stage_a:last_updates", list(updates.keys()))
            cache.set_value("telephony:stage_a:last_ok", str(frappe.utils.now_datetime()))

            # E2: deterministic links (no sending yet)
            base_url = (frappe.utils.get_url() or "").rstrip("/")
            ticket_link = f"{base_url}/app/hd-ticket/{ticket_id}"
            cache.set_value("telephony:stage_a:last_ticket_link", ticket_link)

            cust = (updates.get("custom_customer") or tvals.get("custom_customer") or "").strip()
            if cust:
                cust_q = frappe.utils.quote(cust)
                confirm_link = f"{base_url}/customer/{cust_q}/tickets/{ticket_id}/confirm"
                cache.set_value("telephony:stage_a:last_customer_confirm_link", confirm_link)
            else:
                confirm_link = ""
                cache.set_value("telephony:stage_a:last_customer_confirm_link", "")

            # F1: draft
            to_email = (comm.get("sender") or "").strip().lower()
            cache.set_value("telephony:stage_a:last_autoreply_to", to_email)

            subject = f"Ticket {ticket_id} received"
            if confirm_link:
                body = (
                    f"Hi,\n\n"
                    f"We created Ticket {ticket_id}.\n\n"
                    f"Please confirm the details here:\n{confirm_link}\n\n"
                    f"You can view the ticket here:\n{ticket_link}\n\n"
                    f"Thanks."
                )
            else:
                body = (
                    f"Hi,\n\n"
                    f"We created Ticket {ticket_id}.\n\n"
                    f"You can view the ticket here:\n{ticket_link}\n\n"
                    f"Thanks."
                )

            cache.set_value("telephony:stage_a:last_autoreply_subject", subject)
            cache.set_value("telephony:stage_a:last_autoreply_body", body)

            inbox = (tvals.get("email_account") or "").strip()

            _maybe_send_autoreply(
                comm=comm,
                ticket_id=ticket_id,
                cache=cache,
                to_email=to_email,
                subject=subject,
                body=body,
                inbox=inbox,
                confirm_link=confirm_link,
            )

    except Exception:
        # Do not break inbound processing on parsing issues
        frappe.log_error(title="Stage A v2 intake failed", message=frappe.get_traceback())
        
def _conf_bool(key: str, default: int = 0) -> bool:
    try:
        v = frappe.conf.get(key)
    except Exception:
        v = None
    if v is None:
        v = default
    if isinstance(v, bool):
        return v
    try:
        return int(v) == 1
    except Exception:
        return bool(v)

def _conf_list(key: str, default=None) -> list[str]:
    default = default or []
    try:
        v = frappe.conf.get(key)
    except Exception:
        v = None
    if not v:
        return list(default)
    if isinstance(v, (list, tuple)):
        return [str(x) for x in v if str(x).strip()]
    # allow comma-separated string
    if isinstance(v, str):
        return [s.strip() for s in v.split(",") if s.strip()]
    return list(default)

def _is_valid_email(addr: str) -> bool:
    addr = (addr or "").strip()
    return ("@" in addr) and (" " not in addr) and ("<" not in addr) and (">" not in addr)

def _dedupe_key_for_comm(comm_name: str) -> str:
    return f"telephony:autoreply:sent:{comm_name}"

def _outgoing_sender_for_inbox(inbox: str) -> str:
    inbox = (inbox or "").strip()
    if not inbox:
        return ""
    try:
        return (frappe.db.get_value("Email Account", inbox, "email_id") or "").strip()
    except Exception:
        return ""
    
def _from_header_for_inbox(inbox: str) -> str:
    inbox = (inbox or "").strip()
    if not inbox:
        return ""
    email = (frappe.db.get_value("Email Account", inbox, "email_id") or "").strip()
    if not email:
        return ""
    return f"{inbox} <{email}>"

def _maybe_send_autoreply(
    comm,
    ticket_id: str,
    cache,
    to_email: str,
    subject: str,
    body: str,
    inbox: str,
    confirm_link: str,
):
    def _skip(verdict: str, error: str = ""):
        cache.set_value("telephony:stage_a:last_autoreply_verdict", verdict)
        cache.set_value("telephony:stage_a:last_autoreply_sent_ok", "0")
        cache.set_value("telephony:stage_a:last_autoreply_error", error)

    # 1) global toggle
    if not _conf_bool("telephony_autoreply_enabled", 0):
        _skip("disabled")
        return

    # 2) allowlist inboxes
    allowed = _conf_list("telephony_autoreply_inboxes", ["Routing"])
    if allowed and inbox not in allowed:
        _skip(f"inbox_blocked:{inbox}")
        return

    # 3) denylist: block bounces/system senders  ✅ HERE
    sender = (comm.get("sender") or "").strip().lower()
    subject_in = (comm.get("subject") or "").strip()

    block_prefixes = _conf_list("telephony_autoreply_sender_block_prefixes", ["mailer-daemon", "postmaster"])
    for p in block_prefixes:
        p = (p or "").strip().lower()
        if p and sender.startswith(p + "@"):
            _skip("sender_blocked", f"sender_blocked:{p}")
            return

    block_contains = _conf_list("telephony_autoreply_subject_block_contains", ["Undelivered Mail Returned to Sender"])
    for needle in block_contains:
        needle = (needle or "").strip()
        if needle and needle.lower() in subject_in.lower():
            _skip("subject_blocked", f"subject_blocked:{needle}")
            return

    # 4) validate recipient
    if not _is_valid_email(to_email):
        _skip("invalid_to_email", "invalid_to_email")
        return
    
    # 5) require customer-confirm link
    if _conf_bool("telephony_autoreply_require_customer", 1) and not (confirm_link or "").strip():
        _skip("missing_customer")
        return

    # 6) comm name
    comm_name = (comm.get("name") or "").strip()
    if not comm_name:
        _skip("missing_comm_name", "missing_comm_name")
        return

    # 7) primary dedupe (per inbound Communication)
    dk = _dedupe_key_for_comm(comm_name)
    if cache.get_value(dk):
        _skip("dedupe", "dedupe_already_sent")
        return

    # 7.5) secondary dedupe (ticket + recipient + confirm link) with TTL window
    ttl = _conf_int("telephony_autoreply_dedupe_window_seconds", 86400)
    dk2 = _dedupe_key_secondary(ticket_id, to_email, confirm_link)
    if cache.get_value(dk2):
        _skip("dedupe_secondary", "dedupe_secondary_window")
        return

    # 8) send (never raise)
    from_hdr = _from_header_for_inbox(inbox)
    
    try:
        frappe.sendmail(
            recipients=[to_email],
            sender=from_hdr or "",
            reply_to=(frappe.utils.parseaddr(from_hdr)[1] if from_hdr else None),
            subject=subject,
            message=body.replace("\n", "<br>"),
            reference_doctype="HD Ticket",
            reference_name=ticket_id,
            delayed=False,
        )

        now = str(frappe.utils.now_datetime())
        _cache_set_with_ttl(cache, dk, now, ttl)
        _cache_set_with_ttl(cache, dk2, now, ttl)
        cache.set_value("telephony:stage_a:last_autoreply_verdict", "ok")
        cache.set_value("telephony:stage_a:last_autoreply_sent_ok", "1")
        cache.set_value("telephony:stage_a:last_autoreply_sent_at", now)
        cache.set_value("telephony:stage_a:last_autoreply_sent_to", to_email)
        cache.set_value("telephony:stage_a:last_autoreply_error", "")

    except Exception:
        cache.set_value("telephony:stage_a:last_autoreply_verdict", "error")
        cache.set_value("telephony:stage_a:last_autoreply_sent_ok", "0")
        cache.set_value("telephony:stage_a:last_autoreply_error", frappe.get_traceback())
        frappe.log_error(title="Stage A autoreply send failed", message=frappe.get_traceback())
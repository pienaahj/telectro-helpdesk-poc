# telephony/scripts/intake_stage_a_proof.py
# Deterministic Email Intake Stage A proof harness.
# Safe to run in dev: reads seq/tickets, optionally drains inbox, can send one SMTP test message,
# then pulls via Email Account.receive() and resolves Communication -> HD Ticket.

from __future__ import annotations

import time
import secrets
import smtplib
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

import frappe


DEFAULT_ACCOUNT = "Helpdesk"
DEFAULT_TO = "helpdesk@local.test"
DEFAULT_FROM = "sender@local.test"
DEFAULT_SMTP_HOST = "mail"
DEFAULT_SMTP_PORT = 25


def _as_int(v):
    try:
        return int(v)
    except Exception:
        return None


def snap_seq(tag="SNAP"):
    max_raw = frappe.db.sql("SELECT MAX(name) FROM `tabHD Ticket`")[0][0]
    seq_raw = frappe.db.sql("SELECT next_not_cached_value FROM `hd_ticket_id_seq`")[0][0]
    max_ticket = _as_int(max_raw) or 0
    seq_next = _as_int(seq_raw) or 0
    gap = seq_next - (max_ticket + 1)

    print(f"[{tag}] max={max_ticket} seq_next={seq_next} gap={gap}")
    return {"max": max_ticket, "seq_next": seq_next, "gap": gap, "max_raw": max_raw, "seq_raw": seq_raw}


def list_missing_if_gap():
    s = snap_seq("MISSING-CHECK")
    if s["gap"] <= 0:
        print("[MISSING] none (gap<=0)")
        return []
    missing = []
    for n in range(s["max"] + 1, s["seq_next"]):
        if not frappe.db.exists("HD Ticket", str(n)):
            missing.append(n)
    print("[MISSING]", missing)
    return missing


def receive_account(account_name=DEFAULT_ACCOUNT):
    acc = frappe.get_doc("Email Account", account_name)
    acc.receive()
    frappe.db.commit()


def drain_inbox(account_name=DEFAULT_ACCOUNT, max_loops=5, sleep_s=1):
    """
    Drain backlog: run receive until MAX(ticket) stops changing.
    """
    print(f"[DRAIN] account={account_name} max_loops={max_loops}")
    prev = snap_seq("DRAIN-0")["max"]
    for i in range(1, int(max_loops) + 1):
        receive_account(account_name)
        cur = snap_seq(f"DRAIN-{i}")["max"]
        if cur == prev:
            print("[DRAIN] stable")
            return {"loops": i, "max": cur}
        prev = cur
        if sleep_s:
            time.sleep(float(sleep_s))
    print("[DRAIN] max_loops reached")
    return {"loops": int(max_loops), "max": prev}


def send_smtp_test(
    token=None,
    to_addr=DEFAULT_TO,
    from_addr=DEFAULT_FROM,
    smtp_host=DEFAULT_SMTP_HOST,
    smtp_port=DEFAULT_SMTP_PORT,
    subject_prefix="SMTP intake proof",
):
    if token is None:
        token = secrets.token_hex(5)

    subject = f"[DBG:{token}] {subject_prefix}"

    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="local.test")
    msg.set_content(f"token={token}\n")

    with smtplib.SMTP(smtp_host, int(smtp_port), timeout=10) as s:
        s.ehlo()
        s.send_message(msg)

    out = {
        "token": token,
        "message_id": msg["Message-ID"],
        "subject": subject,
        "from": from_addr,
        "to": to_addr,
        "smtp": f"{smtp_host}:{smtp_port}",
    }
    print("[SMTP] sent ok:", out)
    return out


def resolve_by_token(token):
    like = f"%{token}%"
    rows = frappe.db.sql(
        """
        SELECT name, creation, subject, message_id, reference_doctype, reference_name, sender, recipients
        FROM `tabCommunication`
        WHERE subject LIKE %s OR content LIKE %s
        ORDER BY creation DESC
        LIMIT 1
        """,
        (like, like),
        as_dict=True,
    )
    hit = rows[0] if rows else None
    print("[RESOLVE] token", token, "hit", hit)
    return hit


def resolve_by_msgid(message_id):
    mid = (message_id or "").strip("<>")
    like = f"%{mid}%"
    rows = frappe.db.sql(
        """
        SELECT name, creation, subject, message_id, reference_doctype, reference_name, sender, recipients
        FROM `tabCommunication`
        WHERE message_id LIKE %s
        ORDER BY creation DESC
        LIMIT 1
        """,
        (like,),
        as_dict=True,
    )
    hit = rows[0] if rows else None
    print("[RESOLVE] msgid", mid, "hit", hit)
    return hit


@frappe.whitelist()
def run(
    account_name=DEFAULT_ACCOUNT,
    drain=1,
    send=1,
    token=None,
    max_drain_loops=5,
    drain_sleep_s=1,
):
    """
    Stage A deterministic proof.
    - drain: drain backlog first (1/0)
    - send: send a new SMTP test message (1/0)
    """
    print("\n=== TELEPHONY INTAKE STAGE A PROOF ===")

    if int(drain):
        drain_inbox(account_name=account_name, max_loops=max_drain_loops, sleep_s=drain_sleep_s)

    before = snap_seq("BEFORE")

    sent = None
    if int(send):
        sent = send_smtp_test(token=token)

    hit_token = None
    hit_mid = None

    poll_loops = 16
    poll_sleep_s = 2
    
    poll_success_loop = None
    poll_seconds = None


    for i in range(poll_loops):
        receive_account(account_name)

        if sent:
            hit_token = resolve_by_token(sent["token"])
            hit_mid = resolve_by_msgid(sent["message_id"])

            if hit_mid or hit_token:
                poll_success_loop = i + 1
                poll_seconds = poll_success_loop * poll_sleep_s     
                print(f"[POLL] success on loop {i+1}/{poll_loops}")
                break

        time.sleep(poll_sleep_s)


    if sent and not (hit_mid or hit_token):
        print(f"[POLL] no comm found after {poll_loops} loops; likely Email Account incoming config issue")


    after = snap_seq("AFTER")
    missing = list_missing_if_gap() if after["gap"] != 0 else []
    
    ticket_id = None
    if hit_mid and hit_mid.get("reference_doctype") == "HD Ticket":
        ticket_id = hit_mid.get("reference_name")


    print("\n[PROOF]")
    print("sent:", sent)
    print("hit_token:", hit_token)
    print("hit_mid  :", hit_mid)
    print("before:", before)
    print("after :", after)
    print("ticket_id:", ticket_id)
    print("poll_success_loop:", poll_success_loop, "poll_seconds:", poll_seconds)


    return {
        "sent": sent,
        "hit_token": hit_token,
        "hit_mid": hit_mid,
        "before": before,
        "after": after,
        "missing": missing,
        "ticket_id": ticket_id,
        "poll_success_loop": poll_success_loop,
        "poll_seconds": poll_seconds,
    }

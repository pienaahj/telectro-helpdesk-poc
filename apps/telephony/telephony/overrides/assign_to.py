import json
import frappe


POOL_USER = "helpdesk@local.test"

def _dbg(*args, **kwargs):
    return

def _block_if_needed(*args, **kwargs):
    return

def _parse_assign_to_users(assign_to):
    if not assign_to:
        return []

    if isinstance(assign_to, str):
        s = assign_to.strip()
        if not s:
            return []
        try:
            parsed = json.loads(s)
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if str(x).strip()]
        except Exception:
            return [s]
        return [s]

    if isinstance(assign_to, (list, tuple, set)):
        return [str(x).strip() for x in assign_to if str(x).strip()]

    return [str(assign_to).strip()]

def _cfg_bool(key: str, default: int = 0) -> bool:
    try:
        v = frappe.conf.get(key, default)
    except Exception:
        v = default
    try:
        return int(v) == 1
    except Exception:
        return bool(v)

def _should_raise() -> bool:
    # Default: do NOT raise (avoid upstream transaction rollback)
    return int(frappe.conf.get("telephony_assign_guard_raise", 0) or 0) == 1

def _snap_ticket_seq_state() -> dict:
    """
    Snapshot ID allocator state for HD Ticket.
    Useful to prove: "sequence advanced, but ticket row rolled back".

    Returns:
      {
        "site": "...",
        "max_ticket": 438,
        "seq_next": 440,
        "gap": 1,                 # seq_next - (max_ticket + 1)
        "burned_candidates": [439]  # only if small; else omitted
      }
    """
    out = {
        "site": getattr(getattr(frappe, "local", None), "site", None),
        "max_ticket": None,
        "seq_next": None,
        "gap": None,
    }

    try:
        max_ticket = frappe.db.sql("SELECT MAX(name) FROM `tabHD Ticket`")[0][0]
        out["max_ticket"] = int(max_ticket) if max_ticket is not None else None
    except Exception as e:
        out["max_ticket_err"] = repr(e)

    try:
        seq_next = frappe.db.sql("SELECT next_not_cached_value FROM `hd_ticket_id_seq`")[0][0]
        out["seq_next"] = int(seq_next) if seq_next is not None else None
    except Exception as e:
        out["seq_next_err"] = repr(e)

    try:
        if out["max_ticket"] is not None and out["seq_next"] is not None:
            expected_next = out["max_ticket"] + 1
            out["gap"] = out["seq_next"] - expected_next

            # If the gap is small, list the candidates explicitly (handy for proof logs)
            if 0 < out["gap"] <= 50:
                out["burned_candidates"] = list(range(expected_next, out["seq_next"]))
    except Exception as e:
        out["gap_err"] = repr(e)

    return out


def _log_assign_error(title: str, payload, exc: Exception, extra: dict | None = None):
    """
    Record a structured error log entry without crashing the call further.

    Notes:
    - frappe.log_error(title=..., message=...) will create an Error Log row
    - keep payload small-ish; include snap_before/snap_after for forensic proof
    """
    try:
        msg = {
            "title": title,
            "site": getattr(getattr(frappe, "local", None), "site", None),
            "user": getattr(getattr(frappe, "session", None), "user", None),
            "payload": payload,
            "extra": extra or {},
            "exc": repr(exc),
            "traceback": frappe.get_traceback(),
        }
        frappe.log_error(message=json.dumps(msg, indent=2, default=str), title=title)
    except Exception:
        # never allow logging to break the original flow
        pass


import json
import frappe

@frappe.whitelist()
def add(*args, **kwargs):
    d = dict(kwargs or {})
    if args and isinstance(args[0], dict):
        d.update(args[0])
    _dbg("add:enter", d, args=args, kwargs=kwargs)

    snap_before = _snap_ticket_seq_state()
    _dbg("add:snap_before", snap_before)

    try:
        _block_if_needed(d, "assignment")

        doctype = (d.get("doctype") or d.get("reference_type") or "").strip()
        name = (d.get("name") or d.get("docname") or d.get("reference_name") or "").strip()
        assign_to = d.get("assign_to") or d.get("assign_to_user") or d.get("allocated_to")
        users = _parse_assign_to_users(assign_to)

        _dbg("add:parsed_users", {"assign_to_raw": assign_to, "users": users})

        # ---- Pool short-circuit (true unassigned pool; no core side effects) ----
        # Note: we do not want to allow "assigning" to the pool user as a way to mark "unassigned".
        if doctype == "HD Ticket" and name and users == [POOL_USER]:
            # Close any open ToDos for the old pool user
            pool_todos = frappe.get_all(
                "ToDo",
                filters={
                    "reference_type": "HD Ticket",
                    "reference_name": name,
                    "allocated_to": POOL_USER,
                    "status": "Open",
                },
                fields=["name"],
                ignore_permissions=True,
                limit_page_length=200,
            )
            for td in pool_todos:
                frappe.db.set_value("ToDo", td["name"], "status", "Closed", update_modified=False)

            # Also normalize away any other open ownership ToDos if this path
            # is explicitly being used to return ticket to pool
            open_todos = frappe.get_all(
                "ToDo",
                filters={
                    "reference_type": "HD Ticket",
                    "reference_name": name,
                    "status": "Open",
                },
                fields=["name", "allocated_to"],
                ignore_permissions=True,
                limit_page_length=200,
            )
            for td in open_todos:
                frappe.db.set_value("ToDo", td["name"], "status", "Closed", update_modified=False)

            # True pool = empty assignment
            frappe.db.set_value("HD Ticket", name, "_assign", json.dumps([]), update_modified=False)

            # Defensive cleanup
            frappe.db.delete(
                "DocShare",
                {
                    "share_doctype": "HD Ticket",
                    "share_name": name,
                    "user": POOL_USER,
                },
            )

            _dbg("add:pool_short_circuit", {"doctype": doctype, "name": name, "users": users})
            return []
        # --- Fallback path: delegate to core ---
        if doctype != "HD Ticket" or not name or not users:
            payload = _ensure_core_assign_to_shape(d)
            try:
                core_assign_to.add(payload)
            except Exception as e:
                _log_assign_error(
                    "assign_to.add:core_add_hd_ticket_failed",
                    payload,
                    e,
                    extra={"snap_before": snap_before},
                )
                raise

            if not doctype or not name:
                _dbg("add:fallback_no_target_return_empty", {"doctype": doctype, "name": name})
                return []

            try:
                return _as_assign_list(core_assign_to.get({"doctype": doctype, "name": name}))
            except Exception as e:
                _log_assign_error(
                    "assign_to.add:core_get_failed",
                    {"doctype": doctype, "name": name},
                    e,
                    extra={"snap_before": snap_before},
                )
                return []

        # --- HD Ticket hardened path ---
        seen = set()
        uniq_users = []
        for u in users:
            if u not in seen:
                seen.add(u)
                uniq_users.append(u)

        for u in uniq_users:
            todos = frappe.get_all(
                "ToDo",
                filters={
                    "reference_type": "HD Ticket",
                    "reference_name": name,
                    "allocated_to": u,
                },
                fields=["name", "status", "creation"],
                order_by="creation desc",
                ignore_permissions=True,
                limit_page_length=50,
            )

            if todos:
                newest = todos[0]["name"]

                if (todos[0].get("status") or "") != "Open":
                    frappe.db.set_value("ToDo", newest, "status", "Open", update_modified=False)

                for td in todos[1:]:
                    if (td.get("status") or "") != "Cancelled":
                        frappe.db.set_value("ToDo", td["name"], "status", "Cancelled", update_modified=False)

                continue

            payload = dict(d)
            payload["doctype"] = "HD Ticket"
            payload["name"] = name
            payload["assign_to"] = [u]

            try:
                core_assign_to.add(payload)
            except Exception as e:
                _log_assign_error(
                    "assign_to.add:core_add_hd_ticket_failed",
                    payload,
                    e,
                    extra={"snap_before": snap_before},
                )
                raise

        try:
            _cancel_closed_todos_for_ticket(name)
        except Exception:
            pass

        try:
            open_users = frappe.get_all(
                "ToDo",
                filters={
                    "reference_type": "HD Ticket",
                    "reference_name": name,
                    "status": "Open",
                },
                pluck="allocated_to",
                ignore_permissions=True,
                limit_page_length=200,
            )
            final_users = sorted({(u or "").strip() for u in (open_users or []) if (u or "").strip()})
            frappe.db.set_value("HD Ticket", name, "_assign", json.dumps(final_users), update_modified=False)
        except Exception:
            pass

        _dbg("add:exit", {"doctype": doctype, "name": name})

        try:
            return _as_assign_list(core_assign_to.get({"doctype": "HD Ticket", "name": name}))
        except Exception as e:
            _log_assign_error(
                "assign_to.add:final_get_failed",
                {"doctype": "HD Ticket", "name": name},
                e,
                extra={"snap_before": snap_before},
            )
            return []

    except Exception as e:
        snap_after = _snap_ticket_seq_state()
        _dbg("add:exception", {"err": repr(e), "snap_after": snap_after})

        _log_assign_error(
            "assign_to.add:exception",
            d,
            e,
            extra={"snap_before": snap_before, "snap_after": snap_after},
        )
        raise

    finally:
        snap_final = _snap_ticket_seq_state()
        _dbg("add:snap_final", snap_final)

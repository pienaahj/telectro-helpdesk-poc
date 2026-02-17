import json
import frappe

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


@frappe.whitelist()
def add(*args, **kwargs):
    d = _merge_args_kwargs(*args, **kwargs)
    _dbg("add:enter", d, args=args, kwargs=kwargs)

    # snapshot BEFORE any work
    snap_before = _snap_ticket_seq_state()
    _dbg("add:snap_before", snap_before)

    try:
        _block_if_needed(d, "assignment")

        # Only harden idempotency for HD Ticket (pilot scope)
        doctype = (d.get("doctype") or d.get("reference_type") or "").strip()
        name = (d.get("name") or d.get("docname") or d.get("reference_name") or "").strip()

        assign_to = d.get("assign_to") or d.get("assign_to_user") or d.get("allocated_to")
        users = _parse_assign_to_users(assign_to)

        _dbg("add:parsed_users", {"assign_to_raw": assign_to, "users": users})

        # --- Fallback path: delegate to core, but DO NOT call core.get unless we have a valid target
        if doctype != "HD Ticket" or not name or not users:
            payload = _ensure_core_assign_to_shape(d)

            try:
                core_assign_to.add(payload)
            except Exception as e:
                _log_assign_error(
                    "assign_to.add:core_add_failed",
                    payload,
                    e,
                    extra={"snap_before": snap_before, "doctype": doctype, "name": name},
                )
                raise

            # If we don't have a proper doctype/name, we must not call core.get
            if not doctype or not name:
                _dbg("add:fallback_no_target_return_empty", {"doctype": doctype, "name": name})
                return []

            try:
                return _as_assign_list(core_assign_to.get({"doctype": doctype, "name": name}))
            except Exception as e:
                # IMPORTANT: don't rollback ticket creation because UI-shape failed
                _log_assign_error(
                    "assign_to.add:core_get_failed",
                    {"doctype": doctype, "name": name},
                    e,
                    extra={"snap_before": snap_before},
                )
                return []

        # --- HD Ticket hardened path ---
        # De-dupe incoming list
        seen = set()
        uniq_users = []
        for u in users:
            if u not in seen:
                seen.add(u)
                uniq_users.append(u)

        # For each user: ensure exactly one Open ToDo exists; cancel older duplicates
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

                # Ensure newest is Open
                if (todos[0].get("status") or "") != "Open":
                    frappe.db.set_value("ToDo", newest, "status", "Open", update_modified=False)

                # Cancel older ones
                for td in todos[1:]:
                    if (td.get("status") or "") != "Cancelled":
                        frappe.db.set_value("ToDo", td["name"], "status", "Cancelled", update_modified=False)

                continue

            # None exist -> create via core (keeps core side effects)
            payload = dict(d)
            payload["doctype"] = "HD Ticket"
            payload["name"] = name
            payload["assign_to"] = [u]  # core expects list or JSON-list-string

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

        # Extra hardening: Closed -> Cancelled (prevents reopen-on-save weirdness)
        try:
            _cancel_closed_todos_for_ticket(name)
        except Exception:
            pass

        # Normalize _assign from OPEN ToDos (canonical)
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

        # Return shape: never throw from get()
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
        # snapshot AFTER failure (still inside same transaction context)
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

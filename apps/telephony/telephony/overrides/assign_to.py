import json

import frappe
from frappe.desk.form import assign_to as core_assign_to


POOL_USER = "helpdesk@local.test"


def _dbg(*args, **kwargs):
    return


def _is_admin_like(user: str) -> bool:
    if not user or user == "Administrator":
        return True
    roles = set(frappe.get_roles(user))
    return "System Manager" in roles or "HD Manager" in roles or "Supervisor" in roles


def _is_technician_like(user: str) -> bool:
    if not user or user == "Guest":
        return False
    roles = set(frappe.get_roles(user))
    return "HD Agent" in roles or "Support Team" in roles or "Technician" in roles

def _roles_for(user: str) -> set[str]:
    try:
        return set(frappe.get_roles(user))
    except Exception:
        return set()


def _is_operational_intervention_user(user: str) -> bool:
    """
    Users allowed to intervene in assignment state for the pilot.
    Keep this narrow.
    """
    if not user or user == "Administrator":
        return True

    roles = _roles_for(user)

    allowed = {
        "System Manager",
        "Pilot Admin",
        "TELECTRO-POC Role - Supervisor Governance",
        "TELECTRO-POC Role - Coordinator Ops",
    }
    return bool(roles & allowed)


def _is_regular_agent_user(user: str) -> bool:
    """
    Broad bucket for normal operational users who may work tickets
    but must not use the generic assign dialog for reassignment.
    """
    if not user or user == "Guest":
        return False

    if _is_operational_intervention_user(user):
        return False

    roles = _roles_for(user)

    return bool(
        roles
        & {
            "TELECTRO-POC Role - Tech",
            "TELECTRO-POC Role - Coordinator Ops",
            "Agent",
            "Support Team",
        }
    )


def _get_hd_ticket_assignment_state(name: str) -> dict:
    doc = frappe.get_doc("HD Ticket", name)

    raw_assign = doc.get("_assign")
    if isinstance(raw_assign, str):
        s = raw_assign.strip()
        if not s:
            assign_users = []
        else:
            try:
                parsed = json.loads(s)
                if isinstance(parsed, list):
                    assign_users = [str(x).strip() for x in parsed if str(x).strip()]
                else:
                    assign_users = [s]
            except Exception:
                assign_users = [s]
    elif isinstance(raw_assign, list):
        assign_users = [str(x).strip() for x in raw_assign if str(x).strip()]
    else:
        assign_users = []

    open_todo_users = frappe.get_all(
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
    open_todo_users = sorted({(u or "").strip() for u in (open_todo_users or []) if (u or "").strip()})

    fulfilment_party = (doc.get("custom_fulfilment_party") or "").strip()

    return {
        "doc": doc,
        "assign_users": assign_users,
        "open_todo_users": open_todo_users,
        "effective_users": open_todo_users or assign_users,
        "is_pool": not open_todo_users and not assign_users,
        "fulfilment_party": fulfilment_party,
    }

def _get_hd_ticket_state(name: str) -> dict:
    doc = frappe.get_doc("HD Ticket", name)

    current_assign = doc.get("_assign")
    if isinstance(current_assign, str):
        try:
            current_assign = json.loads(current_assign)
        except Exception:
            current_assign = [current_assign] if current_assign.strip() else []
    elif not isinstance(current_assign, list):
        current_assign = []

    current_assign = [str(x).strip() for x in current_assign if str(x).strip()]

    open_todos = frappe.get_all(
        "ToDo",
        filters={
            "reference_type": "HD Ticket",
            "reference_name": name,
            "status": "Open",
        },
        fields=["name", "allocated_to"],
        ignore_permissions=True,
        limit_page_length=50,
    )
    open_users = sorted({(r.get("allocated_to") or "").strip() for r in open_todos if (r.get("allocated_to") or "").strip()})

    return {
        "doc": doc,
        "assign": current_assign,
        "open_users": open_users,
        "is_pool": not open_users and not current_assign,
        "fulfilment_party": (doc.get("custom_fulfilment_party") or "").strip(),
    }


def _throw_assign_block(msg: str):
    frappe.throw(msg)


def _block_if_needed(d, action: str):
    payload = _ensure_core_assign_to_shape(d)
    doctype = payload.get("doctype")
    name = payload.get("name")
    target_users = payload.get("assign_to") or []
    target_users = [str(x).strip() for x in target_users if str(x).strip()]

    if doctype != "HD Ticket" or not name:
        return

    current_user = getattr(getattr(frappe, "session", None), "user", None) or ""
    state = _get_hd_ticket_assignment_state(name)
    effective_users = state["effective_users"]

    _dbg(
        "guard:state",
        {
            "action": action,
            "current_user": current_user,
            "target_users": target_users,
            "effective_users": effective_users,
            "is_pool": state["is_pool"],
            "fulfilment_party": state["fulfilment_party"],
        },
    )

    # Administrator remains a development escape hatch.
    # This avoids self-lockout while the pilot rules are still evolving.
    if current_user == "Administrator":
        return

    # Pilot accountability rule:
    # Generic Assign To may only assign an HD Ticket from a true zero-owner base.
    #
    # In the TELECTRO pilot, assignment means accountable owner, not contributor list.
    # If a ticket already has an effective owner, adding another user through the
    # generic Assign dialog would create parallel accountability.
    #
    # Reassignment/handoff must happen through an approved flow that closes the old
    # owner's Open ToDo and opens exactly one new owner ToDo.
    if action == "assignment" and effective_users:
        if state["fulfilment_party"] == "Partner":
            frappe.throw(
                "Partner-owned tickets cannot be reassigned here. "
                "Please use the approved Partner flow."
            )

        if target_users == effective_users:
            frappe.throw("This ticket is already assigned.")

        frappe.throw(
            "This ticket already has an accountable owner. "
            "Use the approved handoff/reassignment action instead of adding another assignee."
        )

    # Generic remove is not the allowed release path for any non-Administrator user.
    # Release should go through the controlled pilot Release action so the pool
    # invariant is preserved and the reason is captured.
    if action == "assignment_remove":
        frappe.throw("Use the Release action to remove assignment from a ticket.")

    # Privileged operational intervention users are allowed through from a zero-owner base.
    #
    # Because the single-owner guard above already blocked owned tickets, this only
    # allows supervisor/coordinator assignment when the ticket is currently unowned.
    if _is_operational_intervention_user(current_user):
        return

    # Conservative: only enforce technician/agent restrictions for regular agents.
    if not _is_regular_agent_user(current_user):
        return

    # Partner-owned tickets: regular agents must not mutate generic assignment state.
    if state["fulfilment_party"] == "Partner":
        frappe.throw("Partner-owned tickets cannot be reassigned here. Please ask a supervisor.")

    # Existing ticket in true pool:
    # allow only self-claim through generic assign.
    if state["is_pool"]:
        if len(target_users) == 1 and target_users[0] == current_user:
            return
        frappe.throw("Tickets in pool can only be claimed by yourself.")

    # Existing assigned ticket:
    # regular agents may not use generic assign to release or reassign.
    #
    # Most owned-ticket cases are already blocked by the pilot accountability rule
    # above. Keep this as a defensive fallback.
    if action == "assignment":
        if target_users == [POOL_USER]:
            frappe.throw("Use the Release action to return a ticket to pool.")

        if len(target_users) == 1 and target_users[0] == current_user and effective_users == [current_user]:
            frappe.throw("This ticket is already assigned to you.")

        frappe.throw("You cannot reassign existing tickets from this dialog. Use the approved actions.")


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
            if 0 < out["gap"] <= 50:
                out["burned_candidates"] = list(range(expected_next, out["seq_next"]))
    except Exception as e:
        out["gap_err"] = repr(e)

    return out


def _log_assign_error(title: str, payload, exc: Exception, extra: dict | None = None):
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
        pass


def _ensure_core_assign_to_shape(d: dict) -> dict:
    payload = dict(d or {})

    doctype = (payload.get("doctype") or payload.get("reference_type") or "").strip()
    name = (payload.get("name") or payload.get("docname") or payload.get("reference_name") or "").strip()
    assign_to = (
        payload.get("assign_to")
        or payload.get("assign_to_user")
        or payload.get("allocated_to")
        or payload.get("owner")
        or payload.get("user")
    )

    users = _parse_assign_to_users(assign_to)

    payload["doctype"] = doctype
    payload["name"] = name
    payload["assign_to"] = users

    return payload


def _as_assign_list(value):
    """
    Be tolerant about core return shapes.
    """
    if value is None:
        return []

    if isinstance(value, list):
        return value

    if isinstance(value, tuple):
        return list(value)

    if isinstance(value, str):
        s = value.strip()
        if not s:
            return []
        try:
            parsed = json.loads(s)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            return [s]
        return [s]

    return [value]


def _cancel_closed_todos_for_ticket(name: str):
    """
    Keep only open ownership ToDos meaningful for the ticket.
    Older closed/cancelled duplicates are not needed for active ownership state.
    """
    todos = frappe.get_all(
        "ToDo",
        filters={
            "reference_type": "HD Ticket",
            "reference_name": name,
        },
        fields=["name", "status", "allocated_to", "creation"],
        order_by="creation desc",
        ignore_permissions=True,
        limit_page_length=500,
    )

    seen_open = set()

    for td in todos:
        allocated_to = (td.get("allocated_to") or "").strip()
        status = (td.get("status") or "").strip()

        if status == "Open":
            if allocated_to in seen_open:
                frappe.db.set_value("ToDo", td["name"], "status", "Cancelled", update_modified=False)
            else:
                seen_open.add(allocated_to)


def _sync_ticket_assign_from_open_todos(name: str):
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


def _close_open_todos_for_ticket(name: str):
    open_todos = frappe.get_all(
        "ToDo",
        filters={
            "reference_type": "HD Ticket",
            "reference_name": name,
            "status": "Open",
        },
        fields=["name"],
        ignore_permissions=True,
        limit_page_length=200,
    )
    for td in open_todos:
        frappe.db.set_value("ToDo", td["name"], "status", "Closed", update_modified=False)


def _delete_pool_docshare(name: str):
    frappe.db.delete(
        "DocShare",
        {
            "share_doctype": "HD Ticket",
            "share_name": name,
            "user": POOL_USER,
        },
    )


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

        payload = _ensure_core_assign_to_shape(d)
        doctype = payload["doctype"]
        name = payload["name"]
        users = payload["assign_to"]

        _dbg("add:parsed_users", {"assign_to_raw": d.get("assign_to"), "users": users})

        # True pool short-circuit for HD Ticket
        # At this point regular agents have already been blocked above.
        if doctype == "HD Ticket" and name and users == [POOL_USER]:
            _close_open_todos_for_ticket(name)
            frappe.db.set_value("HD Ticket", name, "_assign", json.dumps([]), update_modified=False)
            _delete_pool_docshare(name)
            _dbg("add:pool_short_circuit", {"doctype": doctype, "name": name, "users": users})
            return []

        # Non-HD Ticket or incomplete target: delegate directly to core
        if doctype != "HD Ticket" or not name or not users:
            try:
                core_assign_to.add(payload)
            except Exception as e:
                _log_assign_error(
                    "assign_to.add:core_add_failed",
                    payload,
                    e,
                    extra={"snap_before": snap_before},
                )
                raise

            if not doctype or not name:
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

        # HD Ticket hardened path
        seen = set()
        uniq_users = []
        for u in users:
            u = (u or "").strip()
            if u and u not in seen:
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

            one_payload = dict(payload)
            one_payload["assign_to"] = [u]

            try:
                core_assign_to.add(one_payload)
            except Exception as e:
                _log_assign_error(
                    "assign_to.add:core_add_hd_ticket_failed",
                    one_payload,
                    e,
                    extra={"snap_before": snap_before},
                )
                raise

        try:
            _cancel_closed_todos_for_ticket(name)
        except Exception:
            pass

        try:
            _sync_ticket_assign_from_open_todos(name)
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
        
@frappe.whitelist()
def remove(*args, **kwargs):
    d = dict(kwargs or {})
    if args and isinstance(args[0], dict):
        d.update(args[0])

    _dbg("remove:enter", d, args=args, kwargs=kwargs)
    snap_before = _snap_ticket_seq_state()
    _dbg("remove:snap_before", snap_before)

    try:
        # Important:
        # For HD Ticket, generic remove must not become a side door for
        # technician release/unassign. The policy gate must run before any
        # core mutation.
        _block_if_needed(d, "assignment_remove")

        payload = _ensure_core_assign_to_shape(d)
        doctype = payload["doctype"]
        name = payload["name"]

        assign_to_users = payload.get("assign_to") or []
        if isinstance(assign_to_users, str):
            assign_to_user = assign_to_users.strip()
        elif isinstance(assign_to_users, (list, tuple)):
            assign_to_user = (assign_to_users[0] or "").strip() if assign_to_users else None
        else:
            assign_to_user = str(assign_to_users).strip() if assign_to_users else None

        if not doctype or not name or not assign_to_user:
            frappe.throw("remove() requires doctype, name, and assign_to")

        try:
            core_assign_to.remove(doctype, name, assign_to_user)
        except Exception as e:
            _log_assign_error(
                "assign_to.remove:core_remove_failed",
                {
                    "doctype": doctype,
                    "name": name,
                    "assign_to": assign_to_user,
                },
                e,
                extra={"snap_before": snap_before},
            )
            raise

        if doctype == "HD Ticket" and name:
            try:
                _cancel_closed_todos_for_ticket(name)
            except Exception:
                pass

            try:
                _sync_ticket_assign_from_open_todos(name)
            except Exception:
                pass

            try:
                return _as_assign_list(core_assign_to.get({"doctype": "HD Ticket", "name": name}))
            except Exception as e:
                _log_assign_error(
                    "assign_to.remove:final_get_failed",
                    {"doctype": "HD Ticket", "name": name},
                    e,
                    extra={"snap_before": snap_before},
                )
                return []

        if doctype and name:
            try:
                return _as_assign_list(core_assign_to.get({"doctype": doctype, "name": name}))
            except Exception as e:
                _log_assign_error(
                    "assign_to.remove:core_get_failed",
                    {"doctype": doctype, "name": name},
                    e,
                    extra={"snap_before": snap_before},
                )
                return []

        return []

    except Exception as e:
        snap_after = _snap_ticket_seq_state()
        _dbg("remove:exception", {"err": repr(e), "snap_after": snap_after})

        _log_assign_error(
            "assign_to.remove:exception",
            d,
            e,
            extra={"snap_before": snap_before, "snap_after": snap_after},
        )
        raise

    finally:
        snap_final = _snap_ticket_seq_state()
        _dbg("remove:snap_final", snap_final)
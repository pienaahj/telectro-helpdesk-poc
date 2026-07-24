from __future__ import annotations

from typing import Any

import frappe


TECH_WORKSPACE = "TELECTRO-POC Tech"

PILOT_WORKSPACES = (
    "TELECTRO-POC Tech",
    "TELECTRO-POC Ops",
    "TELECTRO-POC Coordinator",
    "TELECTRO-POC Partner",
)

OBSOLETE_REPORTS = (
    "My HD Tickets",
    "TELECTRO-POC My Tickets",
    "TELECTRO Unassigned War Room",
    "Unclaimed Missing Group Over 60m",
    "Unclaimed Missing Group Over 4H",
    "Partner Acceptance Review",
)

CANONICAL_REPORTS = {
    "My Tickets": {
        "is_standard": "Yes",
        "module": "FTelephony",
        "report_type": "Script Report",
        "ref_doctype": "HD Ticket",
    },
    "TELECTRO Unclaimed War Room": {
        "is_standard": "Yes",
        "module": "FTelephony",
        "report_type": "Script Report",
        "ref_doctype": "HD Ticket",
    },
    "Tickets Assigned to Partner": {
        "is_standard": "Yes",
        "module": "FTelephony",
        "report_type": "Script Report",
        "ref_doctype": "HD Ticket",
    },
    "Coordinator Uplift History": {
        "is_standard": "Yes",
        "module": "FTelephony",
        "report_type": "Script Report",
        "ref_doctype": "HD Ticket",
    },
}

WAR_ROOM_URL = (
    "/app/query-report/"
    "TELECTRO%20Unclaimed%20War%20Room"
)


def _canonical_report_issues() -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []

    for report_name, expected in CANONICAL_REPORTS.items():
        if not frappe.db.exists("Report", report_name):
            issues.append(
                {
                    "type": "missing_canonical_report",
                    "report": report_name,
                }
            )
            continue

        report = frappe.get_doc(
            "Report",
            report_name,
        )

        for fieldname, expected_value in expected.items():
            actual_value = report.get(fieldname)

            if actual_value == expected_value:
                continue

            issues.append(
                {
                    "type": "canonical_report_mismatch",
                    "report": report_name,
                    "field": fieldname,
                    "expected": expected_value,
                    "actual": actual_value,
                }
            )

        if report.disabled:
            issues.append(
                {
                    "type": "canonical_report_disabled",
                    "report": report_name,
                }
            )

    return issues


def _obsolete_report_references() -> list[dict[str, Any]]:
    references: list[dict[str, Any]] = []

    specs = (
        (
            "Workspace Link",
            "link_to",
            (
                "name",
                "parent",
                "label",
                "link_to",
            ),
        ),
        (
            "Workspace Shortcut",
            "link_to",
            (
                "name",
                "parent",
                "label",
                "link_to",
            ),
        ),
        (
            "Number Card",
            "report_name",
            (
                "name",
                "label",
                "report_name",
            ),
        ),
        (
            "Dashboard Chart",
            "report_name",
            (
                "name",
                "chart_name",
                "report_name",
            ),
        ),
    )

    for doctype, fieldname, fields in specs:
        if not frappe.db.exists("DocType", doctype):
            continue

        meta = frappe.get_meta(doctype)

        if not meta.get_field(fieldname):
            continue

        usable_fields = [
            field
            for field in fields
            if field == "name"
            or meta.get_field(field)
        ]

        rows = frappe.get_all(
            doctype,
            filters={
                fieldname: [
                    "in",
                    list(OBSOLETE_REPORTS),
                ]
            },
            fields=usable_fields,
        )

        for row in rows:
            references.append(
                {
                    "doctype": doctype,
                    "reference_field": fieldname,
                    "row": row,
                }
            )

    return references


def _workspace_identity_hits() -> list[str]:
    hits: list[str] = []

    for workspace_name in PILOT_WORKSPACES:
        if not frappe.db.exists(
            "Workspace",
            workspace_name,
        ):
            continue

        workspace = frappe.get_doc(
            "Workspace",
            workspace_name,
        )

        workspace_text = frappe.as_json(
            workspace.as_dict()
        )

        if "@local.test" in workspace_text:
            hits.append(workspace_name)

    return sorted(hits)


def _tech_workspace_issues() -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []

    if not frappe.db.exists(
        "Workspace",
        TECH_WORKSPACE,
    ):
        return [
            {
                "type": "missing_workspace",
                "workspace": TECH_WORKSPACE,
            }
        ]

    workspace = frappe.get_doc(
        "Workspace",
        TECH_WORKSPACE,
    )

    stale_links = [
        {
            "label": row.label,
            "link_to": row.link_to,
        }
        for row in workspace.links
        if (
            row.label == "My HD Tickets"
            or row.link_to in OBSOLETE_REPORTS
        )
    ]

    if stale_links:
        issues.append(
            {
                "type": "obsolete_workspace_links",
                "rows": stale_links,
            }
        )

    my_tickets = [
        row
        for row in workspace.links
        if row.label == "My Tickets"
    ]

    if len(my_tickets) != 1:
        issues.append(
            {
                "type": "my_tickets_link_count",
                "actual": len(my_tickets),
                "expected": 1,
            }
        )
    else:
        row = my_tickets[0]

        expected = {
            "link_to": "My Tickets",
            "link_type": "Report",
            "is_query_report": 1,
            "report_ref_doctype": "HD Ticket",
        }

        for fieldname, expected_value in expected.items():
            actual_value = row.get(fieldname)

            if actual_value != expected_value:
                issues.append(
                    {
                        "type": "my_tickets_link_mismatch",
                        "field": fieldname,
                        "expected": expected_value,
                        "actual": actual_value,
                    }
                )

    queue_headers = [
        row
        for row in workspace.links
        if (
            row.type == "Card Break"
            and row.label == "Ticket queues"
        )
    ]

    if len(queue_headers) != 1:
        issues.append(
            {
                "type": "ticket_queue_header_count",
                "actual": len(queue_headers),
                "expected": 1,
            }
        )
    elif queue_headers[0].link_count != 3:
        issues.append(
            {
                "type": "ticket_queue_link_count",
                "actual": queue_headers[0].link_count,
                "expected": 3,
            }
        )

    partner_shortcuts = [
        row
        for row in workspace.shortcuts
        if row.label == "TELECTRO - Partner Queue"
    ]

    if len(partner_shortcuts) != 1:
        issues.append(
            {
                "type": "partner_queue_shortcut_count",
                "actual": len(partner_shortcuts),
                "expected": 1,
            }
        )
    else:
        row = partner_shortcuts[0]

        expected = {
            "type": "Report",
            "link_to": "Tickets Assigned to Partner",
            "report_ref_doctype": "HD Ticket",
            "stats_filter": None,
            "url": None,
        }

        for fieldname, expected_value in expected.items():
            actual_value = row.get(fieldname)

            if actual_value != expected_value:
                issues.append(
                    {
                        "type": "partner_queue_shortcut_mismatch",
                        "field": fieldname,
                        "expected": expected_value,
                        "actual": actual_value,
                    }
                )

    war_room_shortcuts = [
        row
        for row in workspace.shortcuts
        if row.label == "🔥 Unclaimed (War Room)"
    ]

    if len(war_room_shortcuts) != 1:
        issues.append(
            {
                "type": "war_room_shortcut_count",
                "actual": len(war_room_shortcuts),
                "expected": 1,
            }
        )
    else:
        row = war_room_shortcuts[0]

        if row.type != "URL" or row.url != WAR_ROOM_URL:
            issues.append(
                {
                    "type": "war_room_shortcut_mismatch",
                    "actual_type": row.type,
                    "actual_url": row.url,
                    "expected_type": "URL",
                    "expected_url": WAR_ROOM_URL,
                }
            )

    return issues


def verify_report_transport_cleanup() -> dict[str, Any]:
    remaining_reports = [
        report_name
        for report_name in OBSOLETE_REPORTS
        if frappe.db.exists(
            "Report",
            report_name,
        )
    ]

    canonical_issues = _canonical_report_issues()
    workspace_issues = _tech_workspace_issues()
    references = _obsolete_report_references()
    identity_hits = _workspace_identity_hits()

    issues: list[dict[str, Any]] = []

    issues.extend(canonical_issues)
    issues.extend(workspace_issues)

    if remaining_reports:
        issues.append(
            {
                "type": "obsolete_reports_present",
                "reports": remaining_reports,
            }
        )

    if references:
        issues.append(
            {
                "type": "obsolete_report_references",
                "references": references,
            }
        )

    if identity_hits:
        issues.append(
            {
                "type": "workspace_local_identities",
                "workspaces": identity_hits,
            }
        )

    return {
        "ok": not issues,
        "site": frappe.local.site,
        "issue_count": len(issues),
        "issues": issues,
        "remaining_obsolete_reports": (
            remaining_reports
        ),
        "obsolete_reference_count": len(
            references
        ),
        "workspace_identity_hits": identity_hits,
    }


def _set_child_value(
    row: Any,
    fieldname: str,
    value: Any,
    changes: list[dict[str, Any]],
    area: str,
) -> None:
    current = row.get(fieldname)

    if current == value:
        return

    row.set(fieldname, value)

    changes.append(
        {
            "area": area,
            "field": fieldname,
            "before": current,
            "after": value,
        }
    )


def _reconcile_tech_workspace() -> list[dict[str, Any]]:
    workspace = frappe.get_doc(
        "Workspace",
        TECH_WORKSPACE,
    )

    changes: list[dict[str, Any]] = []

    for row in list(workspace.links):
        if row.label == "My Tickets":
            continue

        if (
            row.label == "My HD Tickets"
            or row.link_to in OBSOLETE_REPORTS
        ):
            changes.append(
                {
                    "area": "links",
                    "action": "remove",
                    "label": row.label,
                    "link_to": row.link_to,
                }
            )
            workspace.remove(row)

    my_tickets = [
        row
        for row in workspace.links
        if row.label == "My Tickets"
    ]

    if len(my_tickets) != 1:
        frappe.throw(
            "Expected exactly one My Tickets link "
            f"in {TECH_WORKSPACE}; found "
            f"{len(my_tickets)}."
        )

    my_tickets_row = my_tickets[0]

    for fieldname, value in {
        "link_to": "My Tickets",
        "link_type": "Report",
        "is_query_report": 1,
        "report_ref_doctype": "HD Ticket",
    }.items():
        _set_child_value(
            my_tickets_row,
            fieldname,
            value,
            changes,
            "My Tickets",
        )

    queue_headers = [
        row
        for row in workspace.links
        if (
            row.type == "Card Break"
            and row.label == "Ticket queues"
        )
    ]

    if len(queue_headers) != 1:
        frappe.throw(
            "Expected exactly one Ticket queues "
            f"Card Break in {TECH_WORKSPACE}; "
            f"found {len(queue_headers)}."
        )

    _set_child_value(
        queue_headers[0],
        "link_count",
        3,
        changes,
        "Ticket queues",
    )

    partner_shortcuts = [
        row
        for row in workspace.shortcuts
        if row.label == "TELECTRO - Partner Queue"
    ]

    if len(partner_shortcuts) != 1:
        frappe.throw(
            "Expected exactly one Partner Queue "
            f"shortcut in {TECH_WORKSPACE}; "
            f"found {len(partner_shortcuts)}."
        )

    partner_row = partner_shortcuts[0]

    for fieldname, value in {
        "type": "Report",
        "link_to": "Tickets Assigned to Partner",
        "report_ref_doctype": "HD Ticket",
        "stats_filter": None,
        "url": None,
    }.items():
        _set_child_value(
            partner_row,
            fieldname,
            value,
            changes,
            "Partner Queue",
        )

    war_room_shortcuts = [
        row
        for row in workspace.shortcuts
        if row.label == "🔥 Unclaimed (War Room)"
    ]

    if len(war_room_shortcuts) != 1:
        frappe.throw(
            "Expected exactly one Unclaimed War "
            f"Room shortcut in {TECH_WORKSPACE}; "
            f"found {len(war_room_shortcuts)}."
        )

    war_room_row = war_room_shortcuts[0]

    for fieldname, value in {
        "type": "URL",
        "link_to": None,
        "report_ref_doctype": None,
        "stats_filter": None,
        "url": WAR_ROOM_URL,
    }.items():
        _set_child_value(
            war_room_row,
            fieldname,
            value,
            changes,
            "Unclaimed War Room",
        )

    if changes:
        workspace.save(ignore_permissions=True)

    return changes


def ensure_report_transport_cleanup() -> dict[str, Any]:
    canonical_issues = _canonical_report_issues()

    if canonical_issues:
        frappe.throw(
            "Canonical Report verification failed:\n"
            + frappe.as_json(
                canonical_issues,
                indent=2,
            )
        )

    workspace_changes = (
        _reconcile_tech_workspace()
    )

    remaining_references = (
        _obsolete_report_references()
    )

    if remaining_references:
        frappe.throw(
            "Obsolete Reports are still referenced "
            "after Workspace reconciliation:\n"
            + frappe.as_json(
                remaining_references,
                indent=2,
            )
        )

    deleted_reports: list[str] = []

    for report_name in OBSOLETE_REPORTS:
        if not frappe.db.exists(
            "Report",
            report_name,
        ):
            continue

        report = frappe.get_doc(
            "Report",
            report_name,
        )

        if report.is_standard == "Yes":
            frappe.throw(
                "Refusing to delete standard Report "
                f"{report_name!r}."
            )

        if report.module != "Helpdesk":
            frappe.throw(
                "Refusing to delete obsolete Report "
                f"{report_name!r} from unexpected "
                f"module {report.module!r}."
            )

        frappe.delete_doc(
            "Report",
            report_name,
            force=1,
            ignore_permissions=True,
        )

        deleted_reports.append(report_name)

    if workspace_changes or deleted_reports:
        frappe.clear_cache()

    verification = verify_report_transport_cleanup()

    if not verification["ok"]:
        frappe.throw(
            "Report transport cleanup did not reach "
            "the expected state:\n"
            + frappe.as_json(
                verification["issues"],
                indent=2,
            )
        )

    return {
        "ok": True,
        "site": frappe.local.site,
        "workspace_change_count": len(
            workspace_changes
        ),
        "workspace_changes": workspace_changes,
        "deleted_report_count": len(
            deleted_reports
        ),
        "deleted_reports": deleted_reports,
        "verification": verification,
    }


def apply_report_transport_cleanup() -> dict[str, Any]:
    """Explicit transactional entry point."""

    try:
        result = ensure_report_transport_cleanup()
        frappe.db.commit()
        return result
    except Exception:
        frappe.db.rollback()
        raise


def after_migrate() -> dict[str, Any]:
    """Reconcile Report transport after fixture import."""

    result = ensure_report_transport_cleanup()

    frappe.logger("telephony").info(
        "Report transport cleanup verified: "
        "%s Workspace change(s), "
        "%s obsolete Report(s) deleted",
        result["workspace_change_count"],
        result["deleted_report_count"],
    )

    return result

"""
Contextual assignment-mode policy resolution.

Assignment Policy controls whether automatic assignment is allowed.
Service Coverage controls technician eligibility.

This module performs no assignment or database writes.
"""

import frappe

from telephony.service_coverage import get_ticket_context


POLICY_DOCTYPE = "TELECTRO Assignment Policy"

ROUND_ROBIN = "Round Robin"
TRUE_POOL = "True Pool"


def _clean(value) -> str:
    return str(value or "").strip()


def get_matching_assignment_policy(
    *,
    customer: str | None = None,
    campus: str | None = None,
    service_area: str | None = None,
) -> dict | None:
    """
    Return the most-specific enabled assignment policy.

    Precedence:
      1. Customer/Campus
      2. Campus
      3. Customer
      4. Default

    None means no explicit policy exists. The existing assignment
    behavior must then remain authoritative.

    Duplicate enabled policies at the same specificity are rejected
    rather than allowing arbitrary policy selection.
    """
    customer = _clean(customer)
    campus = _clean(campus)
    service_area = _clean(service_area)

    if not service_area:
        return None

    # During a Type C production release, the candidate runtime is
    # activated before database migration creates new DocType tables.
    #
    # Preserve existing routing behavior during that interval.
    # Operational policy activation must follow successful migration.
    if not frappe.db.table_exists(POLICY_DOCTYPE):
        return None

    match_specs = [
        (
            "Customer/Campus",
            bool(customer and campus),
            {
                "customer": customer,
                "campus": campus,
            },
        ),
        (
            "Campus",
            bool(campus),
            {
                "campus": campus,
            },
        ),
        (
            "Customer",
            bool(customer),
            {
                "customer": customer,
            },
        ),
        (
            "Default",
            True,
            {},
        ),
    ]

    for scope, should_run, context_filters in match_specs:
        if not should_run:
            continue

        filters = {
            "enabled": 1,
            "coverage_scope": scope,
            "service_area": service_area,
            **context_filters,
        }

        rows = frappe.get_all(
            POLICY_DOCTYPE,
            filters=filters,
            fields=[
                "name",
                "coverage_scope",
                "customer",
                "campus",
                "service_area",
                "assignment_mode",
            ],
            order_by="name asc",
            limit_page_length=2,
        )

        if len(rows) > 1:
            frappe.throw(
                "Conflicting enabled Assignment Policies "
                "for {0} / {1}. Check records: {2}".format(
                    scope,
                    service_area,
                    ", ".join(
                        _clean(row.get("name"))
                        for row in rows
                    ),
                )
            )

        if rows:
            policy = dict(rows[0])

            mode = _clean(policy.get("assignment_mode"))

            if mode not in {ROUND_ROBIN, TRUE_POOL}:
                frappe.throw(
                    "Invalid Assignment Mode on policy {0}.".format(
                        policy.get("name")
                    )
                )

            return policy

    return None


def get_ticket_assignment_policy(ticket_or_name) -> dict | None:
    """
    Resolve assignment policy using the existing ticket context.

    Read-only; does not create ToDos, alter _assign, modify
    Assignment Rules, or change native round-robin cursors.
    """
    context = get_ticket_context(ticket_or_name)

    return get_matching_assignment_policy(
        customer=context["customer"],
        campus=context["campus"],
        service_area=context["service_area"],
    )


def requires_cctv_context_triage(ticket_or_name) -> bool:
    """
    Identify CCTV tickets whose Customer/Campus context is incomplete.

    These tickets must not fall through to automatic native team
    assignment until both Customer and Campus are known.

    This is a read-only context decision. It does not alter
    Assignment Policies, ownership, or native assignment rules.

    Complete CCTV contexts and all non-CCTV service areas retain
    their existing assignment behaviour.
    """
    context = get_ticket_context(ticket_or_name)

    if context["service_area"] != "CCTV":
        return False

    return not (
        context["customer"]
        and context["campus"]
    )

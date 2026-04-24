import frappe


ACTIVE_EXCLUDED_STATUSES = ("Closed", "Archived", "Resolved")


@frappe.whitelist()
def assigned_to_partner_now() -> int:
    return frappe.db.sql(
        """
        select count(*)
        from `tabHD Ticket` t
        where coalesce(t.custom_fulfilment_party, '') = 'Partner'
          and coalesce(t.status, '') not in %s
        """,
        (ACTIVE_EXCLUDED_STATUSES,),
    )[0][0]


@frappe.whitelist()
def submitted_by_partner_now() -> int:
    return frappe.db.sql(
        """
        select count(*)
        from `tabHD Ticket` t
        where coalesce(t.custom_request_source, '') = 'Partner'
          and coalesce(t.status, '') not in %s
        """,
        (ACTIVE_EXCLUDED_STATUSES,),
    )[0][0]
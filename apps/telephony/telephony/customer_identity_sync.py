import frappe


def _hd_customers_for(erp_customer):
    return frappe.get_all(
        "HD Customer",
        filters={"custom_erp_customer": erp_customer},
        pluck="name",
        limit_page_length=2,
    )


def sync_ticket_customer_identity(doc, method=None):
    """Synchronise HD Customer and ERPNext Customer without changing requester."""

    hd_customer = str(doc.get("customer") or "").strip()
    erp_customer = str(doc.get("custom_customer") or "").strip()

    if not hd_customer and not erp_customer:
        return

    if hd_customer:
        mapped_erp = frappe.db.get_value(
            "HD Customer",
            hd_customer,
            "custom_erp_customer",
        )

        if erp_customer and mapped_erp != erp_customer:
            frappe.throw(
                "HD Customer and ERPNext Customer do not match.",
                frappe.ValidationError,
            )

        if mapped_erp:
            matches = _hd_customers_for(mapped_erp)

            if len(matches) != 1 or matches[0] != hd_customer:
                frappe.throw(
                    "Ambiguous HD Customer to ERPNext Customer mapping.",
                    frappe.ValidationError,
                )

            if not erp_customer:
                doc.set("custom_customer", mapped_erp)

        return

    matches = _hd_customers_for(erp_customer)

    if len(matches) > 1:
        frappe.throw(
            "Multiple HD Customers map to this ERPNext Customer.",
            frappe.ValidationError,
        )

    if len(matches) == 1:
        doc.set("customer", matches[0])

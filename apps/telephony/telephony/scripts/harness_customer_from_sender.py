import frappe

def run(emails=None):
    """
    Harness: test _customer_from_sender(email) and show contact+dynamic-link chain.
    Run via:
      bench --site frontend execute telephony.scripts.harness_customer_from_sender.run --kwargs '{"emails":["a@b.com"]}'
    """
    from telephony.telectro_intake import _customer_from_sender

    if emails is None:
        emails = [
            "customer.a@local.test",
            "sender@local.test",
            "tester@local.test",
            "doesnotexist@local.test",
            "",
        ]

    def contact_chain(email: str):
        email = (email or "").strip().lower()
        if not email:
            return None, []

        contact = None

        # Contact Email child table path (most common)
        if frappe.db.exists("DocType", "Contact Email"):
            contact = frappe.db.get_value("Contact Email", {"email_id": email}, "parent")

        # fallback: Contact.email_id
        if not contact and frappe.db.exists("DocType", "Contact"):
            contact = frappe.db.get_value("Contact", {"email_id": email}, "name")

        if not contact:
            return None, []

        links = []
        if frappe.db.exists("DocType", "Dynamic Link"):
            links = frappe.get_all(
                "Dynamic Link",
                filters={"parenttype": "Contact", "parent": contact, "link_doctype": "Customer"},
                pluck="link_name",
                limit_page_length=5,
                ignore_permissions=True,
            ) or []

        return contact, links

    print("Customer mapping harness")
    print("-" * 80)

    for e in emails:
        cust, reason = _customer_from_sender(e)
        contact, links = contact_chain(e)

        print(f"email: {e!r}")
        print(f"  -> mapped_customer: {cust!r}")
        print(f"  -> reason:         {reason!r}")
        print(f"  -> contact:        {contact!r}")
        print(f"  -> customer_links: {links!r}")
        print("-" * 80)
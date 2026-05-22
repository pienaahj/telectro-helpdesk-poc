import frappe


@frappe.whitelist()
def is_call_integration_enabled():
    return False


@frappe.whitelist()
def customer_article_search(query=None):
    return []
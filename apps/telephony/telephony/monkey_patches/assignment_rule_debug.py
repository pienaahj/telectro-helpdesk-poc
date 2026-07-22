import json

import frappe
from frappe.automation.doctype.assignment_rule.assignment_rule import AssignmentRule


def _debug_comments_enabled() -> bool:
    return bool(frappe.conf.get("telectro_rule_debug_comments"))


def apply():
    if getattr(AssignmentRule, "_telectro_patched_debug", False):
        return

    orig_apply_assign = AssignmentRule.apply_assign

    def wrapped_apply_assign(self, doc):
        if _debug_comments_enabled() and getattr(doc, "doctype", None) == "HD Ticket":
            payload = {
                "rule_name": getattr(self, "name", None),
                "document_type": getattr(self, "document_type", None),
                "doc": f"{doc.doctype}:{doc.name}",
            }

            frappe.get_doc(
                {
                    "doctype": "Comment",
                    "comment_type": "Comment",
                    "reference_doctype": "HD Ticket",
                    "reference_name": doc.name,
                    "content": "TELECTRO_RULE_DEBUG " + json.dumps(payload, default=str),
                }
            ).insert(ignore_permissions=True)

        return orig_apply_assign(self, doc)

    AssignmentRule.apply_assign = wrapped_apply_assign
    AssignmentRule._telectro_patched_debug = True
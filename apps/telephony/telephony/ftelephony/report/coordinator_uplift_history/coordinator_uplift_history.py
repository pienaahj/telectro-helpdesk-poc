import frappe


def execute(filters=None):
    columns = [
        {
            "label": "Time",
            "fieldname": "creation",
            "fieldtype": "Datetime",
            "width": 180,
        },
        {
            "label": "Target User",
            "fieldname": "reference_name",
            "fieldtype": "Link",
            "options": "User",
            "width": 220,
        },
        {
            "label": "Actor",
            "fieldname": "owner",
            "fieldtype": "Link",
            "options": "User",
            "width": 220,
        },
        {
            "label": "Details",
            "fieldname": "content",
            "fieldtype": "Data",
            "width": 700,
        },
    ]

    data = frappe.get_all(
        "Comment",
        filters={
            "reference_doctype": "User",
            "comment_type": "Info",
        },
        or_filters=[
            ["Comment", "content", "like", "Coordinator uplift granted%"],
            ["Comment", "content", "like", "Coordinator uplift revoked%"],
        ],
        fields=[
            "creation",
            "owner",
            "reference_name",
            "content",
        ],
        order_by="creation desc",
    )

    return columns, data
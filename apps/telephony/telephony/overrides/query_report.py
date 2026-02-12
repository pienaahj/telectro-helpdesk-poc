import frappe
from frappe.desk import query_report as core_query_report

OLD = "TELECTRO Unassigned War Room"
NEW = "TELECTRO Unclaimed War Room"

# What the RPC usually sends for these methods
_ALLOWED_GET_SCRIPT_KW = {"report_name"}
_ALLOWED_RUN_KW = {
    "report_name",
    "filters",
    "ignore_prepared_report",
    "are_default_filters",
    "dashboard_filters",
    "parent_doc",
}


def _swap_report_name(name: str | None) -> str | None:
    if not name:
        return name
    name = str(name).strip()
    return NEW if name == OLD else name


def _rewrite_first_arg(args: tuple, new_first: str) -> tuple:
    if not args:
        return (new_first,)
    a = list(args)
    a[0] = new_first
    return tuple(a)


def _clean_kwargs(kwargs: dict, allowed: set[str]) -> dict:
    # Strip frappe internal / unexpected keys like "cmd"
    return {k: v for k, v in (kwargs or {}).items() if k in allowed}


@frappe.whitelist()
def get_script(*args, **kwargs):
    report_name = (kwargs or {}).get("report_name") or (args[0] if args else None)
    swapped = _swap_report_name(report_name)

    cleaned = _clean_kwargs(kwargs, _ALLOWED_GET_SCRIPT_KW)
    if "report_name" in cleaned:
        cleaned["report_name"] = swapped
        return core_query_report.get_script(**cleaned)

    # Fallback: positional first arg
    return core_query_report.get_script(*_rewrite_first_arg(args, swapped))


@frappe.whitelist()
def run(*args, **kwargs):
    report_name = (kwargs or {}).get("report_name") or (args[0] if args else None)
    swapped = _swap_report_name(report_name)

    cleaned = _clean_kwargs(kwargs, _ALLOWED_RUN_KW)
    if "report_name" in cleaned:
        cleaned["report_name"] = swapped

        # ✅ Inject default filters for My HD Tickets so Query Report doesn't KeyError on first load
        if swapped == "My HD Tickets":
            raw = cleaned.get("filters")

            # Normalize filters to dict
            if raw in (None, "", "null"):
                filters = {}
            elif isinstance(raw, str):
                try:
                    filters = frappe.parse_json(raw) or {}
                except Exception:
                    filters = {}
            elif isinstance(raw, dict):
                filters = raw
            else:
                filters = {}

            # Always provide key so %(user)s never KeyErrors
            if "user" not in filters or not filters.get("user"):
                filters["user"] = frappe.session.user

            cleaned["filters"] = frappe.as_json(filters)  # safest across versions
            cleaned.pop("are_default_filters", None)

            frappe.errprint(
            f"[MyHD DEBUG] swapped={swapped} filters={filters}"
            )

            return core_query_report.run(**cleaned)

        frappe.log_error(
            f"My HD Tickets cleaned before core",
            "TELECTRO My HD Tickets debug"
        )

    return core_query_report.run(*_rewrite_first_arg(args, swapped))



import frappe

JOB_NAME = "pull_pilot_inboxes.run"


def _find_scheduled_job():
    return frappe.db.get_value(
        "Scheduled Job Type",
        {"method": JOB_NAME},
        ["name", "stopped", "frequency"],
        as_dict=True,
    )


def _recent_errors(limit=10):
    # Best-effort: look for recent errors mentioning the job method
    rows = frappe.get_all(
        "Error Log",
        filters={"error": ["like", f"%{JOB_NAME}%"]},
        fields=["name", "creation", "method", "error"],
        order_by="creation desc",
        limit_page_length=limit,
    )
    return rows


def _redis_breadcrumbs(prefix="telephony:pull_pilot_in"):
    # Best-effort: only if Redis cache is available
    try:
        cache = frappe.cache()
        # Not all cache backends support key listing; handle gracefully.
        keys = []
        if hasattr(cache, "get_keys"):
            keys = cache.get_keys(prefix)  # type: ignore[attr-defined]
        return {"supported": True, "prefix": prefix, "keys": keys[:50]}
    except Exception as e:
        return {"supported": False, "prefix": prefix, "error": repr(e)}


def run(site=None):
    print("site:", frappe.local.site)
    print("user:", frappe.session.user)

    # 1) Scheduled Job Type exists?
    job = _find_scheduled_job()
    if not job:
        print(f"\n❌ Scheduled Job Type not found for method: {JOB_NAME}")
        print("Next: check Scheduled Job Type list and ensure telephony app is installed on this site.")
        return

    print("\n✅ Scheduled Job Type found:")
    print("  name:", job["name"])
    print("  method:", JOB_NAME)
    print("  stopped:", job["stopped"])
    print("  frequency:", job.get("frequency"))

    # 2) Recent errors mentioning job
    errs = _recent_errors(limit=5)
    print("\nRecent Error Log entries mentioning the job:", len(errs))
    for r in errs:
        # Don't spam full traceback unless needed
        err_preview = (r.get("error") or "")[:200].replace("\n", " ")
        print(f" - {r['creation']} {r['name']} preview: {err_preview}")

    # 3) Breadcrumbs (best-effort)
    bc = _redis_breadcrumbs()
    print("\nBreadcrumb cache probe:")
    if bc["supported"]:
        print("  supported: yes")
        print("  prefix:", bc["prefix"])
        print("  keys(sample):", bc["keys"])
    else:
        print("  supported: no")
        print("  error:", bc.get("error"))

    print("\nDone. If intake still feels silent, next step is a controlled test email and checking Communication creation.")
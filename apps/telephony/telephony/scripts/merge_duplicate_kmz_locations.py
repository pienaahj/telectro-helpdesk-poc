import re
from typing import Any

import frappe


DUP_SUFFIX_RE = re.compile(r"^(?P<base>.+) \((?P<num>\d+)\)$")


def _has_usable_coords(row: dict[str, Any]) -> bool:
    lat = float(row.get("latitude") or 0)
    lon = float(row.get("longitude") or 0)
    return lat != 0.0 and lon != 0.0


def _is_incomplete(row: dict[str, Any]) -> bool:
    return (
        not _has_usable_coords(row)
        and not row.get("custom_kmz_metadata_json")
    )


def _get_location(name: str) -> dict[str, Any] | None:
    row = frappe.db.get_value(
        "Location",
        name,
        [
            "name",
            "location_name",
            "parent_location",
            "is_group",
            "latitude",
            "longitude",
            "custom_kmz_geometry_type",
            "custom_kmz_metadata_json",
            "custom_kmz_source",
        ],
        as_dict=True,
    )
    return row


def _find_pairs(parent_location: str | None = None, limit: int = 10000):
    filters = {
        "is_group": 0,
        "custom_kmz_geometry_type": "Point",
        "location_name": ["like", "%(%)"],
    }

    if parent_location:
        filters["parent_location"] = parent_location

    dupes = frappe.get_all(
        "Location",
        filters=filters,
        fields=[
            "name",
            "location_name",
            "parent_location",
            "is_group",
            "latitude",
            "longitude",
            "custom_kmz_geometry_type",
            "custom_kmz_metadata_json",
            "custom_kmz_source",
        ],
        order_by="parent_location, location_name",
        limit_page_length=limit,
    )

    pairs = []

    for dupe in dupes:
        m = DUP_SUFFIX_RE.match(dupe.location_name or "")
        if not m:
            continue

        base_label = m.group("base")
        parent = dupe.parent_location

        base_name = frappe.db.get_value(
            "Location",
            {
                "parent_location": parent,
                "location_name": base_label,
                "is_group": 0,
            },
            "name",
        )

        if not base_name:
            continue

        base = _get_location(base_name)
        if not base:
            continue

        if not _is_incomplete(base):
            continue

        if not _has_usable_coords(dupe):
            continue

        if not dupe.get("custom_kmz_metadata_json"):
            continue

        pairs.append(
            {
                "base": base,
                "dupe": dupe,
                "base_label": base_label,
            }
        )

    return pairs


def _location_link_fields():
    standard = frappe.get_all(
        "DocField",
        filters={"fieldtype": "Link", "options": "Location"},
        fields=["parent", "fieldname"],
        order_by="parent, fieldname",
    )

    custom = frappe.get_all(
        "Custom Field",
        filters={"fieldtype": "Link", "options": "Location"},
        fields=["dt", "fieldname"],
        order_by="dt, fieldname",
    )

    out = []

    for row in standard:
        out.append((row.parent, row.fieldname))

    for row in custom:
        out.append((row.dt, row.fieldname))

    # Keep deterministic and unique
    return sorted(set(out))


def _reference_count(doctype: str, fieldname: str, location_name: str) -> int:
    try:
        return frappe.db.count(doctype, filters={fieldname: location_name})
    except Exception:
        return 0


def _migrate_references(
    old_location: str,
    new_location: str,
    dry_run: bool = True,
):
    migrated = []

    for doctype, fieldname in _location_link_fields():
        count = _reference_count(doctype, fieldname, old_location)
        if not count:
            continue

        migrated.append(
            {
                "doctype": doctype,
                "fieldname": fieldname,
                "count": count,
            }
        )

        if not dry_run:
            frappe.db.sql(
                f"""
                UPDATE `tab{doctype}`
                SET `{fieldname}` = %s
                WHERE `{fieldname}` = %s
                """,
                (new_location, old_location),
            )

    return migrated


def run(
    parent_location: str | None = None,
    dry_run: int = 1,
    commit: int = 0,
    limit: int = 10000,
):
    """
    Merge duplicate KMZ Location labels.

    Pattern:
      base row:  Buildings: Bakery
                 no coordinates / no KMZ metadata

      dupe row:  Buildings: Bakery (2)
                 usable coordinates / KMZ metadata

    Action:
      - migrate Location link references from base -> dupe
      - delete base Location
      - rename dupe.location_name to base label

    Always run dry_run=1 first.
    """

    dry_run_bool = bool(int(dry_run))
    commit_bool = bool(int(commit))

    if commit_bool:
        dry_run_bool = False

    pairs = _find_pairs(parent_location=parent_location, limit=int(limit))

    print("dry_run:", int(dry_run_bool), "commit:", int(commit_bool))
    print("parent_location:", parent_location or "<all>")
    print("candidate pairs:", len(pairs))

    changed = 0
    skipped = 0

    for pair in pairs:
        base = pair["base"]
        dupe = pair["dupe"]
        base_label = pair["base_label"]

        print()
        print("BASE :", base.name, "|", base.location_name)
        print("DUPE :", dupe.name, "|", dupe.location_name)
        print("TARGET LABEL:", base_label)

        migrated = _migrate_references(
            old_location=base.name,
            new_location=dupe.name,
            dry_run=dry_run_bool,
        )

        if migrated:
            print("reference migrations:")
            for row in migrated:
                print(" -", row["doctype"], row["fieldname"], row["count"])
        else:
            print("reference migrations: none")

        if dry_run_bool:
            changed += 1
            continue

        # Delete incomplete base first, freeing the clean human label.
        frappe.delete_doc(
            "Location",
            base.name,
            ignore_permissions=True,
            force=True,
        )

        frappe.db.set_value(
            "Location",
            dupe.name,
            "location_name",
            base_label,
            update_modified=False,
        )

        changed += 1

    if commit_bool:
        frappe.db.commit()
        print()
        print("committed")

    print()
    print("done")
    print("changed:", changed)
    print("skipped:", skipped)
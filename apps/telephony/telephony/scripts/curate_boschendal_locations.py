import re

import frappe


ROOT = "Boschendal"

EXPECTED_GROUPS = {
    "Boschendal": "Pilot Sites",
    "Boschendal - Areas": "Boschendal",
    "Boschendal - Buildings": "Boschendal",
    "Boschendal - Links": "Boschendal",
    "Boschendal - Network Nodes": "Boschendal",
    "Boschendal - Other": "Boschendal",
    "Boschendal - Residents": "Boschendal",
}

# delete_id, delete_label, delete_parent,
# keep_id, keep_label, keep_parent
DUPLICATE_PAIRS = [
    (
        "kmzf0dc9b2317a2344d07e677e9",
        "Links: Oaks -> Goodhope (2)",
        "Boschendal - Links",
        "kmzdc4c7a32dc53a38285c65f07",
        "Links: Oaks -> Goodhope",
        "Boschendal - Links",
    ),
    (
        "kmz7740022d51c8b7519f005146",
        "Other: Orchards BOH (2)",
        "Boschendal - Other",
        "kmz2b2e4db2f34e89711f9e0026",
        "Other: Orchards BOH",
        "Boschendal - Network Nodes",
    ),
    (
        "kmza2fe6e4dcc77a94cac57db1d",
        "Other: Jeffrey (Woodwork) (2)",
        "Boschendal - Other",
        "kmz916d079a979ef6627df2bc87",
        "Other: Jeffrey (Woodwork)",
        "Boschendal - Network Nodes",
    ),
    (
        "kmza6da13bad8aed33fb1ba5c1a",
        "Other: FOH Melvina (2)",
        "Boschendal - Other",
        "kmzc82a279b4d801c8dc9c23b0c",
        "Other: FOH Melvina",
        "Boschendal - Network Nodes",
    ),
    (
        "kmz7d51c710dbfc0d26d9f8ba9f",
        "Other: Bike Container (2)",
        "Boschendal - Other",
        "kmz0ad254d8189b5d6b8614bb8b",
        "Other: Bike Container",
        "Boschendal - Network Nodes",
    ),
    (
        "kmz53a0c0f660fdb87d0ee69f6b",
        "Other: Transformer (2)",
        "Boschendal - Other",
        "kmzcb1ef362bedb3f10ded19456",
        "Other: Transformer",
        "Boschendal - Network Nodes",
    ),
    (
        "kmzaa1e41f9a6cd6b374f427556",
        "Other: Hostels Cam (2)",
        "Boschendal - Other",
        "kmz0efc0df80ee95367e8e2535c",
        "Other: Hostels Cam",
        "Boschendal - Network Nodes",
    ),
    (
        "kmz3b44eb1480ddc4d6bb2145bd",
        "Other: Transformer 2 (2)",
        "Boschendal - Other",
        "kmz404365ca9f15d9e55c51b147",
        "Other: Transformer 2",
        "Boschendal - Network Nodes",
    ),
    (
        "kmz19cc4be06e3ba12da6050428",
        "Other: Cannery Row (2)",
        "Boschendal - Other",
        "kmz9b934450b77b154da119d4fe",
        "Other: Cannery Row",
        "Boschendal - Network Nodes",
    ),
    (
        "kmz29d8e0d37232a3617e47aa11",
        "Other: Charles Edmonds (2)",
        "Boschendal - Other",
        "kmz5286ab9e5888dca4fba37e3d",
        "Other: Charles Edmonds",
        "Boschendal - Network Nodes",
    ),
    (
        "kmz35ebc1f4f15ada414500008e",
        "Other: Tracey Van Wijk (2)",
        "Boschendal - Other",
        "kmza420fd26ecd1189bca03e378",
        "Other: Tracey Van Wijk",
        "Boschendal - Network Nodes",
    ),
    (
        "kmza4206e9f13103e0aaee732f5",
        "Other: The Villa (2)",
        "Boschendal - Other",
        "kmz91797461f035fb0df9e12099",
        "Other: The Villa",
        "Boschendal - Network Nodes",
    ),
    (
        "kmzb2f75ffaab603e30b22bf630",
        "Other: Jaco Rossouw (2)",
        "Boschendal - Other",
        "kmz6fb56a7ac032f6cbb136803a",
        "Other: Jaco Rossouw",
        "Boschendal - Network Nodes",
    ),
    (
        "kmz3f848aa55bb24fb989e7245c",
        "Other: Excelsior PTZ (2)",
        "Boschendal - Other",
        "kmzafcc5d80b601a01a688cd16c",
        "Other: Excelsior PTZ",
        "Boschendal - Network Nodes",
    ),
    (
        "kmz8b98dad2a414486f863f65d9",
        "Other: Droebaan Cam (2)",
        "Boschendal - Other",
        "kmzbe5088a52743ff6050719b8d",
        "Other: Droebaan Cam",
        "Boschendal - Network Nodes",
    ),
    (
        "kmz80fa5ff625f358e92dc23039",
        "Other: Trout Cottage (2)",
        "Boschendal - Other",
        "kmzbc3f69becf3f3d186e97aceb",
        "Other: Trout Cottage",
        "Boschendal - Network Nodes",
    ),
    (
        "kmz51559d992f9553bd0c141dfc",
        "Other: Charles Quint Relay (2)",
        "Boschendal - Other",
        "kmzb5b3af8c102d47a1c5ee7417",
        "Other: Charles Quint Relay",
        "Boschendal - Network Nodes",
    ),
    (
        "kmz254a498fb7e21887080de43e",
        "Other: Chef Christiaan Cambell (2)",
        "Boschendal - Other",
        "kmz79a51829cdea9f9e56e51afb",
        "Other: Chef Christiaan Cambell",
        "Boschendal - Network Nodes",
    ),
    (
        "kmz5d8928b1d4c24dff8331ade0",
        "Other: Hennie Snyman (2)",
        "Boschendal - Other",
        "kmz18c23782fd94b7596f95c1a2",
        "Other: Hennie Snyman",
        "Boschendal - Network Nodes",
    ),
    (
        "kmz8ee2c1edc43029685c5cc9ce",
        "Other: Rachelsfontein (2)",
        "Boschendal - Other",
        "kmz10eca87159b5fe57f1a2b0be",
        "Other: Rachelsfontein",
        "Boschendal - Network Nodes",
    ),
    (
        "kmz09b376d1fd25c899929d7080",
        "Other: Elzanne Calitz (2)",
        "Boschendal - Other",
        "kmzf360288540126b7ee4d8d81f",
        "Other: Elzanne Calitz",
        "Boschendal - Network Nodes",
    ),
    (
        "kmz3440cc062308997c1ca22b73",
        "Other: Norma Kennedy (2)",
        "Boschendal - Other",
        "kmz5deb07b56f632f0466d941d7",
        "Other: Norma Kennedy",
        "Boschendal - Network Nodes",
    ),
    (
        "kmzb0d5a916d02abb12f4871437",
        "Other: Oaks Cottages (2)",
        "Boschendal - Other",
        "kmzce25b8eba36ab151a6966b9c",
        "Other: Oaks Cottages",
        "Boschendal - Network Nodes",
    ),
    (
        "kmz6e84e0ea47d565f351105b86",
        "Other: Excelsior (2)",
        "Boschendal - Other",
        "kmz0414a53c731a20587b02bf40",
        "Other: Excelsior",
        "Boschendal - Network Nodes",
    ),
    (
        "kmzc51d871585b5af5aa1f07c15",
        "Other: Deli Uplink (2)",
        "Boschendal - Other",
        "kmzcf2e39ddf61e6de9b8e133fa",
        "Other: Deli Uplink",
        "Boschendal - Network Nodes",
    ),
    (
        "kmz357196828b1aeab0b37579f7",
        "Other: Sawmill Gate Cam (2)",
        "Boschendal - Other",
        "kmz2599857b3715f9583779bcbc",
        "Other: Sawmill Gate Cam",
        "Boschendal - Network Nodes",
    ),
]

RAW_DUPLICATE_PAIRS = [
    (
        "kmzcb3fa91f58c18a38fe4ba7f9",
        "kmzcb3fa91f58c18a38fe4ba7f9",
        "Boschendal - Network Nodes",
        "kmzfa4e33bc8aa34e33572c10b4",
        "Links: Wireless Connection",
        "Boschendal - Links",
    ),
    (
        "kmzff2de50e0d0e7e8bd5ff76a0",
        "kmzff2de50e0d0e7e8bd5ff76a0",
        "Boschendal - Network Nodes",
        "kmz541dfcc49840528002d76671",
        "Links: Failover Wireless Link",
        "Boschendal - Links",
    ),
]

INCOMPLETE_BASE = (
    "kmz3cd4d52b3498c69eced9718d",
    "Buildings: Untitled Path",
    "Boschendal - Buildings",
    "kmz583f46e72afe62354d5672f2",
)

# name, current_label, target_label, parent, allowed_collision
RENAME_PLAN = [
    (
        "kmz583f46e72afe62354d5672f2",
        "kmz583f46e72afe62354d5672f2",
        "Buildings: Untitled Path",
        "Boschendal - Buildings",
        "kmz3cd4d52b3498c69eced9718d",
    ),
    (
        "kmzdec023e575cbcd31aedd0b5a",
        "kmzdec023e575cbcd31aedd0b5a",
        "Network Nodes: Untitled Path",
        "Boschendal - Network Nodes",
        None,
    ),
    (
        "kmzacd983cd88c586b844e1c73a",
        "kmzacd983cd88c586b844e1c73a",
        "Other: Untitled Path",
        "Boschendal - Other",
        None,
    ),
]

EXPECTED_NUMBERED_AFTER = {
    "kmzd143a045e261af78e9a3fc96": "Other: Splicebox (2)",
}

PAIR_FIELDS = [
    "name",
    "location_name",
    "parent_location",
    "is_group",
    "latitude",
    "longitude",
    "custom_kmz_source",
    "custom_kmz_folder_path",
    "custom_kmz_geometry_type",
    "custom_kmz_metadata_json",
]


def _assert(condition, message):
    if not condition:
        raise RuntimeError(message)


def _norm_path(value):
    parts = [
        part.strip()
        for part in (value or "").split("/")
        if part.strip()
    ]

    out = []

    for part in parts:
        if not out or out[-1] != part:
            out.append(part)

    return " / ".join(out)


def _location(name):
    return frappe.db.get_value(
        "Location",
        name,
        PAIR_FIELDS,
        as_dict=True,
    )


def _subtree_rows():
    root = frappe.db.get_value(
        "Location",
        ROOT,
        ["lft", "rgt"],
        as_dict=True,
    )

    _assert(root, f"Missing Location root: {ROOT}")

    return frappe.get_all(
        "Location",
        filters={
            "lft": [">=", root.lft],
            "rgt": ["<=", root.rgt],
        },
        fields=[
            "name",
            "location_name",
            "parent_location",
            "is_group",
        ],
        order_by="lft asc",
        limit_page_length=0,
    )


def _counts():
    rows = _subtree_rows()

    groups = 0
    leaves = 0
    raw = 0
    numbered = {}

    for row in rows:
        if int(row.get("is_group") or 0):
            groups += 1
            continue

        leaves += 1
        label = row.get("location_name") or ""

        if label.lower().startswith("kmz"):
            raw += 1

        if re.search(r"\s\(\d+\)$", label):
            numbered[row.get("name")] = label

    return len(rows), groups, leaves, raw, numbered


def _link_fields():
    specs = set()

    for row in frappe.get_all(
        "DocField",
        filters={
            "fieldtype": "Link",
            "options": "Location",
        },
        fields=["parent", "fieldname"],
        limit_page_length=0,
    ):
        specs.add(
            (
                row.get("parent"),
                row.get("fieldname"),
            )
        )

    for row in frappe.get_all(
        "Custom Field",
        filters={
            "fieldtype": "Link",
            "options": "Location",
        },
        fields=["dt", "fieldname"],
        limit_page_length=0,
    ):
        specs.add(
            (
                row.get("dt"),
                row.get("fieldname"),
            )
        )

    return sorted(specs)


def _references(name, link_fields):
    refs = []

    for doctype, fieldname in link_fields:
        try:
            count = frappe.db.count(
                doctype,
                filters={fieldname: name},
            )
        except Exception as exc:
            raise RuntimeError(
                f"Could not inspect "
                f"{doctype}.{fieldname}: {exc}"
            ) from exc

        if count:
            refs.append(
                (
                    doctype,
                    fieldname,
                    count,
                )
            )

    return refs


def _delete_manifest():
    items = []

    for pair in DUPLICATE_PAIRS + RAW_DUPLICATE_PAIRS:
        items.append(
            (
                pair[0],
                pair[1],
                pair[2],
            )
        )

    items.append(INCOMPLETE_BASE[:3])

    return items


def _check_groups():
    for name, parent in EXPECTED_GROUPS.items():
        row = frappe.db.get_value(
            "Location",
            name,
            [
                "location_name",
                "parent_location",
                "is_group",
            ],
            as_dict=True,
        )

        _assert(
            row,
            f"Missing expected group: {name}",
        )

        _assert(
            row.location_name == name,
            f"Group label drift: {name}",
        )

        _assert(
            row.parent_location == parent,
            f"Group parent drift: {name}",
        )

        _assert(
            int(row.is_group or 0) == 1,
            f"Not a group: {name}",
        )


def _check_duplicate_pair(pair):
    (
        delete_id,
        delete_label,
        delete_parent,
        keep_id,
        keep_label,
        keep_parent,
    ) = pair

    duplicate = _location(delete_id)
    canonical = _location(keep_id)

    _assert(
        duplicate,
        f"Missing duplicate: {delete_id}",
    )

    _assert(
        canonical,
        f"Missing canonical row: {keep_id}",
    )

    _assert(
        int(duplicate.is_group or 0) == 0,
        f"Duplicate is a group: {delete_id}",
    )

    _assert(
        duplicate.location_name == delete_label,
        f"Duplicate label drift: {delete_id}",
    )

    _assert(
        duplicate.parent_location == delete_parent,
        f"Duplicate parent drift: {delete_id}",
    )

    _assert(
        canonical.location_name == keep_label,
        f"Canonical label drift: {keep_id}",
    )

    _assert(
        canonical.parent_location == keep_parent,
        f"Canonical parent drift: {keep_id}",
    )

    _assert(
        duplicate.custom_kmz_source
        == canonical.custom_kmz_source,
        f"Source differs: {delete_id}",
    )

    _assert(
        duplicate.custom_kmz_geometry_type
        == canonical.custom_kmz_geometry_type,
        f"Geometry differs: {delete_id}",
    )

    _assert(
        float(duplicate.latitude or 0)
        == float(canonical.latitude or 0)
        and
        float(duplicate.longitude or 0)
        == float(canonical.longitude or 0),
        f"Coordinates differ: {delete_id}",
    )

    _assert(
        duplicate.custom_kmz_metadata_json
        == canonical.custom_kmz_metadata_json,
        f"KMZ metadata differs: {delete_id}",
    )

    _assert(
        _norm_path(
            duplicate.custom_kmz_folder_path
        )
        == _norm_path(
            canonical.custom_kmz_folder_path
        ),
        f"Normalised folder differs: {delete_id}",
    )


def _check_incomplete_base():
    (
        delete_id,
        delete_label,
        delete_parent,
        keep_id,
    ) = INCOMPLETE_BASE

    base = _location(delete_id)
    replacement = _location(keep_id)

    _assert(
        base and replacement,
        "Incomplete-base pair missing",
    )

    _assert(
        base.location_name == delete_label,
        "Incomplete-base label drift",
    )

    _assert(
        base.parent_location == delete_parent,
        "Incomplete-base parent drift",
    )

    _assert(
        float(base.latitude or 0) == 0.0
        and float(base.longitude or 0) == 0.0,
        "Incomplete base now has coordinates",
    )

    _assert(
        not base.custom_kmz_metadata_json,
        "Incomplete base now has KMZ metadata",
    )

    _assert(
        replacement.location_name == keep_id,
        "Replacement label drift",
    )

    _assert(
        replacement.parent_location == delete_parent,
        "Replacement parent drift",
    )

    _assert(
        float(replacement.latitude or 0) != 0.0
        and float(replacement.longitude or 0) != 0.0,
        "Replacement lacks coordinates",
    )

    _assert(
        bool(replacement.custom_kmz_metadata_json),
        "Replacement lacks KMZ metadata",
    )


def _check_renames():
    delete_ids = {
        item[0]
        for item in _delete_manifest()
    }

    for (
        name,
        current_label,
        target_label,
        parent,
        allowed_collision,
    ) in RENAME_PLAN:
        row = frappe.db.get_value(
            "Location",
            name,
            [
                "location_name",
                "parent_location",
                "is_group",
            ],
            as_dict=True,
        )

        _assert(
            row,
            f"Missing rename source: {name}",
        )

        _assert(
            int(row.is_group or 0) == 0,
            f"Rename source is a group: {name}",
        )

        _assert(
            row.location_name == current_label,
            f"Rename source label drift: {name}",
        )

        _assert(
            row.parent_location == parent,
            f"Rename source parent drift: {name}",
        )

        matches = frappe.get_all(
            "Location",
            filters={
                "location_name": target_label,
            },
            pluck="name",
            limit_page_length=0,
        )

        unexpected = [
            match
            for match in matches
            if match != name
            and not (
                match == allowed_collision
                and match in delete_ids
            )
        ]

        _assert(
            not unexpected,
            f"Unexpected collision for "
            f"{target_label!r}: {unexpected}",
        )


def _preflight():
    _check_groups()

    (
        total,
        groups,
        leaves,
        raw,
        numbered,
    ) = _counts()

    _assert(
        (
            total,
            groups,
            leaves,
            raw,
            len(numbered),
        )
        == (
            298,
            7,
            291,
            5,
            27,
        ),
        (
            "Unexpected pre-curation counts: "
            f"total={total} "
            f"groups={groups} "
            f"leaves={leaves} "
            f"raw={raw} "
            f"numbered={len(numbered)}"
        ),
    )

    _assert(
        len(DUPLICATE_PAIRS) == 26,
        "Duplicate-pair manifest drift",
    )

    manifest = _delete_manifest()

    _assert(
        len(manifest) == 29,
        "Delete manifest must contain exactly 29 rows",
    )

    _assert(
        len(
            {
                item[0]
                for item in manifest
            }
        )
        == 29,
        "Delete manifest contains duplicate IDs",
    )

    for pair in (
        DUPLICATE_PAIRS
        + RAW_DUPLICATE_PAIRS
    ):
        _check_duplicate_pair(pair)

    _check_incomplete_base()
    _check_renames()

    link_fields = _link_fields()

    for name, _, _ in manifest:
        refs = _references(
            name,
            link_fields,
        )

        _assert(
            not refs,
            (
                f"Delete candidate {name} "
                f"has Location references: {refs}"
            ),
        )

    print("PRECONDITION_TOTAL=298")
    print("PRECONDITION_GROUPS=7")
    print("PRECONDITION_LEAVES=291")
    print("PRECONDITION_RAW_LABELS=5")
    print("PRECONDITION_NUMBERED_LABELS=27")
    print("APPROVED_DELETE_COUNT=29")
    print("APPROVED_RENAME_COUNT=3")
    print("DELETE_REFERENCES_CLEAR=YES")
    print("BOSCHENDAL_CURATION_PREFLIGHT=PASS")


def _apply():
    for name, label, parent in _delete_manifest():
        print(
            f"DELETE "
            f"ID={name!r} "
            f"LABEL={label!r} "
            f"PARENT={parent!r}"
        )

        frappe.delete_doc(
            "Location",
            name,
            ignore_permissions=True,
        )

    for (
        name,
        current_label,
        target_label,
        _,
        _,
    ) in RENAME_PLAN:
        print(
            f"RENAME "
            f"ID={name!r} "
            f"FROM={current_label!r} "
            f"TO={target_label!r}"
        )

        frappe.db.set_value(
            "Location",
            name,
            "location_name",
            target_label,
            update_modified=False,
        )


def _postflight():
    (
        total,
        groups,
        leaves,
        raw,
        numbered,
    ) = _counts()

    _assert(
        (
            total,
            groups,
            leaves,
            raw,
            len(numbered),
        )
        == (
            269,
            7,
            262,
            0,
            1,
        ),
        (
            "Unexpected post-curation counts: "
            f"total={total} "
            f"groups={groups} "
            f"leaves={leaves} "
            f"raw={raw} "
            f"numbered={len(numbered)}"
        ),
    )

    _assert(
        numbered == EXPECTED_NUMBERED_AFTER,
        f"Unexpected numbered labels: {numbered}",
    )

    for name, _, _ in _delete_manifest():
        _assert(
            not frappe.db.exists(
                "Location",
                name,
            ),
            f"Deleted row still exists: {name}",
        )

    for (
        name,
        _,
        target_label,
        parent,
        _,
    ) in RENAME_PLAN:
        row = frappe.db.get_value(
            "Location",
            name,
            [
                "location_name",
                "parent_location",
            ],
            as_dict=True,
        )

        _assert(
            row,
            f"Renamed row missing: {name}",
        )

        _assert(
            row.location_name == target_label,
            f"Rename failed: {name}",
        )

        _assert(
            row.parent_location == parent,
            f"Parent drift after rename: {name}",
        )

    for pair in (
        DUPLICATE_PAIRS
        + RAW_DUPLICATE_PAIRS
    ):
        _assert(
            frappe.db.exists(
                "Location",
                pair[3],
            ),
            f"Canonical row missing: {pair[3]}",
        )

    _check_groups()

    print("POSTCONDITION_TOTAL=269")
    print("POSTCONDITION_GROUPS=7")
    print("POSTCONDITION_LEAVES=262")
    print("POSTCONDITION_RAW_LABELS=0")
    print("POSTCONDITION_NUMBERED_LABELS=1")
    print(
        "RETAINED_NUMBERED_LABEL="
        "'Other: Splicebox (2)'"
    )
    print("BOSCHENDAL_CURATION_POSTFLIGHT=PASS")


def run(dry_run=1, commit=0):
    """
    Curate the proven Boschendal DEV Location dataset.

    Safe modes:
      dry_run=1, commit=0
        validate only; no writes

      commit=1
        validate; apply; post-validate; commit

    dry_run=0, commit=0 is deliberately refused.

    This script does not parse or reinterpret the KMZ.
    It applies only the exact curation manifest proven
    against the current DEV Boschendal Location tree.
    """
    dry_run = bool(int(dry_run))
    commit = bool(int(commit))

    if commit:
        dry_run = False

    if not dry_run and not commit:
        raise ValueError(
            "Refusing uncommitted write mode. "
            "Use dry_run=1,commit=0 or commit=1."
        )

    print("=== Boschendal Location curation ===")
    print(f"site={frappe.local.site}")
    print(f"dry_run={int(dry_run)}")
    print(f"commit={int(commit)}")
    print()

    _preflight()

    if dry_run:
        print()
        print("DRY_RUN_COMPLETE=YES")
        print("DATABASE_MUTATED=NO")

        return {
            "ok": True,
            "dry_run": True,
            "delete_count": 29,
            "rename_count": 3,
        }

    try:
        print()
        print(
            "=== Applying approved "
            "curation manifest ==="
        )

        _apply()

        print()
        print(
            "=== Post-curation validation ==="
        )

        _postflight()

        frappe.db.commit()

        print()
        print("COMMITTED=YES")
        print(
            "BOSCHENDAL_LOCATION_"
            "CURATION_COMPLETE=YES"
        )

        return {
            "ok": True,
            "committed": True,
            "final_total": 269,
        }

    except Exception:
        frappe.db.rollback()

        print()
        print("ROLLED_BACK=YES")

        raise

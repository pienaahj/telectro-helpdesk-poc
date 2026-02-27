# apps/telephony/telephony/scripts/debug_location_map.py
import json
import frappe


def _short(v, n=220):
    if isinstance(v, str) and len(v) > n:
        return v[:n] + "…"
    return v


def _print_meta():
    meta = frappe.get_meta("Location")
    needles = ("geo", "map", "lat", "lon", "long", "location")

    print("--- Location fields containing map/geo/lat/lon/location ---")
    for f in meta.fields:
        fn = (f.fieldname or "")
        ft = (f.fieldtype or "")
        label = (f.label or "")
        fn_l = fn.lower()

        hit = False
        if ft in ("Geolocation", "Map"):
            hit = True
        else:
            for n in needles:
                if n in fn_l:
                    hit = True
                    break

        if hit:
            fetch_from = getattr(f, "fetch_from", None)
            print(
                f"{fn:28} | {ft:12} | {label:24} | options={f.options} | fetch_from={fetch_from}"
            )

    print("\n--- Core DB columns containing geo/lat/lon/location ---")
    cols = meta.get_valid_columns() or []
    hits = []
    for c in cols:
        cl = c.lower()
        for n in needles:
            if n in cl:
                hits.append(c)
                break
    for c in hits:
        print(" -", c)


def _print_docs(names):
    keys = [
        "latitude",
        "longitude",
        "location",
        "location_name",
        "parent_location",
        "custom_kmz_geometry_type",
        "custom_kmz_metadata_json",
    ]

    print("\n--- Stored values ---")
    for name in names:
        print(f"\n=== {name} ===")
        if not frappe.db.exists("Location", name):
            print("Missing Location doc")
            continue

        d = frappe.get_doc("Location", name)
        dd = d.as_dict()
        for k in keys:
            if k in dd:
                print(f"{k:26} = {_short(d.get(k))}")


def _geo_point(lat, lon):
    # GeoJSON uses [lon, lat]
    return json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "Point",
                        "coordinates": [float(lon), float(lat)],
                    },
                }
            ],
        }
    )


def _has_location(name, fieldname="location"):
    val = frappe.db.get_value("Location", name, fieldname)
    return bool(val) and val not in ("", "null", "None")


def _set_location_field(
    names,
    fieldname="location",
    *,
    roots_only=True,
    force=False,
):
    """
    Write GeoJSON Point into `fieldname` using latitude/longitude.

    Safe defaults:
    - roots_only=True: skip child Locations (parent_location set). This prevents
      collapsing manual leaf anchors (like Boschendal gate) back to parent coords
      when latitude/longitude are fetch_from parent.
    - force=False: never overwrite an existing GeoJSON value unless explicitly forced.
    """
    print(f"\n--- Writing {fieldname} from lat/lon (safe) ---")
    print(f"roots_only={roots_only} force={force}")

    for name in names:
        print(f"\n--- {name} ---")
        if not frappe.db.exists("Location", name):
            print("Missing")
            continue

        parent = frappe.db.get_value("Location", name, "parent_location")

        if roots_only and parent:
            print(f"SKIP: child location (parent={parent})")
            continue

        if _has_location(name, fieldname=fieldname) and not force:
            print(f"SKIP: {fieldname} already set (use force=True to overwrite)")
            continue

        d = frappe.get_doc("Location", name)
        lat = d.get("latitude")
        lon = d.get("longitude")
        print("lat/lon:", lat, lon, "(parent:", parent, ")")

        if lat in (None, "", 0) or lon in (None, "", 0):
            print("SKIP: lat/lon empty/zero-ish")
            continue

        # guard: handle strings
        try:
            latf = float(lat)
            lonf = float(lon)
        except Exception as e:
            print("SKIP: lat/lon not numeric:", e)
            continue

        if latf == 0.0 and lonf == 0.0:
            print("SKIP: lat/lon is 0,0")
            continue

        gj = _geo_point(latf, lonf)
        frappe.db.set_value("Location", name, fieldname, gj, update_modified=False)
        print("WROTE", fieldname)


def set_point(name, lat, lon, fieldname="location"):
    """
    Explicitly set a Location GeoJSON point (lon/lat) regardless of parent/lat/lon fetch_from.
    Use this for manual anchors like 'Boschendal' gate.
    """
    if not frappe.db.exists("Location", name):
        raise ValueError(f"Missing Location: {name}")

    gj = _geo_point(float(lat), float(lon))
    frappe.db.set_value("Location", name, fieldname, gj, update_modified=False)
    frappe.db.commit()
    print("Set", name, fieldname, "to point", lat, lon)


def run(
    boschendal="Boschendal",
    pilot_sites="Pilot Sites",
    write_location=False,
    location_field="location",
    roots_only=True,
    force=False,
):
    """
    Debug Location map behavior.

    Params (kwargs):
      boschendal: Location name
      pilot_sites: Location name
      write_location: bool (if True, write GeoJSON point into location_field)
      location_field: fieldname to write (default: "location")
      roots_only: bool (default True) skip children (parent_location set) when writing
      force: bool (default False) overwrite existing GeoJSON when writing
    """
    names = [boschendal, pilot_sites]

    _print_meta()
    _print_docs(names)

    if write_location:
        _set_location_field(
            names,
            fieldname=location_field,
            roots_only=roots_only,
            force=force,
        )
        frappe.db.commit()
        print("\nCommitted.")
        _print_docs(names)
import importlib
import json
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import frappe
import telephony.scripts.import_kmz_locations as imp

importlib.reload(imp)

def _get_match_latlon_from_kmz_meta(meta_json: str, geom_type: str):
    """
    For Points: use meta.first
    For LineString/Polygon: use meta.centroid
    Returns (lat, lon) or (None, None)
    """
    if not meta_json:
        return None, None
    try:
        meta = json.loads(meta_json) if isinstance(meta_json, str) else meta_json
    except Exception:
        return None, None

    gt = (geom_type or "").strip()

    if gt == "Point":
        src = (meta or {}).get("first") or {}
    else:
        src = (meta or {}).get("centroid") or {}

    lon = src.get("lon")
    lat = src.get("lat")
    if lon is None or lat is None:
        return None, None
    return float(lat), float(lon)

def _norm_path(p: str) -> str:
    """Normalize folder paths and remove adjacent duplicates."""
    if not p:
        return ""
    parts = [x.strip() for x in p.split("/") if x.strip()]
    out = []
    for x in parts:
        if not out or out[-1] != x:
            out.append(x)
    return " / ".join(out)


def _unique_location_name(base: str, docname: str) -> str:
    base = (base or "").strip()
    if not base:
        return base

    existing = frappe.db.get_value("Location", {"location_name": base}, "name")
    if (not existing) or existing == docname:
        return base

    for i in range(2, 5000):
        cand = f"{base} ({i})"
        existing = frappe.db.get_value("Location", {"location_name": cand}, "name")
        if (not existing) or existing == docname:
            return cand

    return f"{base} ({docname[-6:]})"


def _parse_kmz(kmz_path: str):
    """
    Build lookup: (geom_type, folder_str) -> list of (lat, lon, label)
    """
    kmz = Path(kmz_path)
    extract_dir = Path("/tmp/kmz_extract_repair")
    extract_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(kmz, "r") as z:
        z.extractall(extract_dir)

    kml_file = extract_dir / "doc.kml"
    tree = ET.parse(str(kml_file))
    root = tree.getroot()

    doc = root.find("kml:Document", imp.KML_NS)
    if doc is None:
        raise ValueError("Invalid KML: Document element not found")

    placemarks = []
    skipped_non_point = 0
    skipped_no_coords = 0
    kept_points = 0
    for pm in doc.findall("kml:Placemark", imp.KML_NS):
        placemarks.append(([], pm))
    for folder, path in imp._iter_folders(doc, []):
        for pm in folder.findall("kml:Placemark", imp.KML_NS):
            placemarks.append((path, pm))

    lookup = {}
    for folder_path, pm in placemarks:
        pname = imp._txt(pm, "kml:name") or "Unnamed"
        res = imp._geom_from_placemark(pm)

        # compat: supports (geom_type, lat, lon) and (geom_type, lat, lon, ...)
        geom_type = lat = lon = None
        if isinstance(res, (list, tuple)) and len(res) >= 3:
            geom_type, lat, lon = res[0], res[1], res[2]
        elif isinstance(res, dict):
            geom_type = res.get("geom_type")
            lat = res.get("lat")
            lon = res.get("lon")

        if not geom_type:
            skipped_non_point += 1
            continue

        gt = str(geom_type)
        if gt not in ("Point", "LineString", "Polygon"):
            skipped_non_point += 1
            continue

        if lat is None or lon is None:
            skipped_no_coords += 1
            continue

        bucket = imp._bucket_for(folder_path, geom_type)

        folder_str = " / ".join(folder_path) if folder_path else ""
        if folder_str and not folder_str.lower().startswith("boschendal"):
            folder_str = "Boschendal / " + folder_str
        elif not folder_str:
            folder_str = "Boschendal"

        folder_str = _norm_path(folder_str)

        label = f"{bucket}: {pname}".strip()

        key2 = (str(geom_type or ""), str(folder_str or ""))
        lookup.setdefault(key2, []).append((float(lat), float(lon), label))

        kept_points += 1
        
    print("parse_kmz: kept_points=", kept_points, "skipped_non_point=", skipped_non_point, "skipped_no_coords=", skipped_no_coords)

    return lookup


def _closest_label(cands, lat, lon, tol=0.0005):
    """
    Find closest candidate within tol degrees (~55m for 0.0005).
    """
    if not cands:
        return None
    best_label = None
    best_d2 = None
    for clat, clon, label in cands:
        d2 = (clat - lat) ** 2 + (clon - lon) ** 2
        if best_d2 is None or d2 < best_d2:
            best_d2 = d2
            best_label = label
    if best_d2 is not None and best_d2 <= (tol ** 2):
        return best_label
    return None


def _get_point_latlon_from_kmz_meta(meta_json: str):
    """
    Use custom_kmz_metadata_json.first {lon,lat} as canonical per-point coords.
    """
    if not meta_json:
        return None, None
    try:
        meta = json.loads(meta_json) if isinstance(meta_json, str) else meta_json
    except Exception:
        return None, None

    first = (meta or {}).get("first") or {}
    lon = first.get("lon")
    lat = first.get("lat")
    if lon is None or lat is None:
        return None, None
    return float(lat), float(lon)


def repair_location_names(
    kmz_path="/import/Boschendal.kmz",
    tol=0.0005,
    dry_run=0,
    only_parent_location=None,
    only_folder_prefix=None,
    limit=10000,
    verbose=1,
):
    """
    Retrospectively repair Location.location_name from KMZ placemark names.

    - Matches by (geom_type, custom_kmz_folder_path) then nearest lat/lon within tol.
    - Uses custom_kmz_metadata_json.first lat/lon (NOT Location.latitude/longitude fetch_from parent).
    - Only updates rows where location_name looks like junk ('kmz%').

    Run with dry_run=1 first.
    """

    # If running via bench execute, we are already connected.
    # Only init/connect if not in a site context.
    if not getattr(frappe.local, "site", None):
        site = "frontend"
        frappe.init(site=site)
        frappe.connect()

    print("connected site:", frappe.local.site)
    print("kmz_path:", kmz_path)
    print("dry_run:", int(bool(dry_run)), "tol:", tol)

    lookup = _parse_kmz(kmz_path)
    print("lookup keys:", len(lookup))

    filters_sql = ""
    params = []

    if only_parent_location:
        filters_sql += " AND parent_location=%s"
        params.append(only_parent_location)

    rows = frappe.db.sql(
        "SELECT name, location_name, parent_location, custom_kmz_folder_path, custom_kmz_geometry_type, custom_kmz_metadata_json "
        "FROM `tabLocation` "
        "WHERE is_group=0 "
        "  AND custom_kmz_geometry_type IN ('Point','LineString','Polygon') "
        "  AND location_name LIKE 'kmz%%' "
        f"{filters_sql} "
        "LIMIT %s",
        tuple(params + [int(limit)]),
        as_dict=True,
    )

    print("rows fetched:", len(rows))

    updated = 0
    missing = 0
    miss_samples = []
    update_samples = []

    pref = _norm_path(only_folder_prefix) if only_folder_prefix else None

    for r in rows:
        docname = r["name"]
        folder_str = _norm_path((r.get("custom_kmz_folder_path") or "").strip())
        geom_type = (r.get("custom_kmz_geometry_type") or "").strip()

        if pref and not folder_str.startswith(pref):
            continue

        lat, lon = _get_match_latlon_from_kmz_meta(
            r.get("custom_kmz_metadata_json") or "",
            r.get("custom_kmz_geometry_type") or "",
        )
        if lat is None or lon is None:
            missing += 1
            if len(miss_samples) < 10:
                miss_samples.append((docname, "no kmz meta coords"))
            continue

        key2 = (str(geom_type or ""), str(folder_str or ""))
        cands = lookup.get(key2)
        label = _closest_label(cands, float(lat), float(lon), tol=float(tol))
        if not label:
            missing += 1
            if len(miss_samples) < 10:
                miss_samples.append((docname, folder_str))
            continue

        label = _unique_location_name(label, docname)

        if dry_run:
            updated += 1
            if len(update_samples) < 10:
                update_samples.append((docname, label))
            continue

        frappe.db.set_value("Location", docname, "location_name", label, update_modified=False)
        updated += 1
        if len(update_samples) < 10:
            update_samples.append((docname, label))

    if not dry_run:
        frappe.db.commit()

    print("repair done. updated:", updated, "missing:", missing)

    if verbose:
        if update_samples:
            print("\nSample updates:")
            for a, b in update_samples:
                print(" -", a, "->", b)
        if miss_samples:
            print("\nSample misses:")
            for a, b in miss_samples:
                print(" -", a, "|", b)

    # only destroy if we were the one who inited
    # (simple heuristic: if site wasn't set before)
    # leaving it alone is safest in bench context.


def run(
    kmz_path="/import/Boschendal.kmz",
    tol=0.0005,
    dry_run=0,
    only_parent_location=None,
    only_folder_prefix=None,
    limit=10000,
    verbose=1,
):
    repair_location_names(
        kmz_path=kmz_path,
        tol=tol,
        dry_run=dry_run,
        only_parent_location=only_parent_location,
        only_folder_prefix=only_folder_prefix,
        limit=limit,
        verbose=verbose,
    )
import zipfile
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import frappe
import hashlib

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

def _leaf_docname(parent_docname: str, location_name: str) -> str:
    raw = (parent_docname or "") + "|" + (location_name or "")
    h = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:24]  # hex = [0-9a-f]
    return f"kmz{h}"  # ✅ strictly alphanumeric

def _safe_docname(s: str, max_len: int = 140) -> str:
    """
    Convert arbitrary text into a Frappe-safe docname.
    - Replace disallowed chars with '-'
    - Collapse whitespace/dashes
    - Append short hash for uniqueness
    """
    raw = (s or "").strip()
    raw = re.sub(r"\s+", " ", raw)

    # Keep only letters, numbers, space, underscore, hyphen, dot
    base = re.sub(r"[^A-Za-z0-9 _\-.]+", "-", raw)
    base = re.sub(r"[\s\-]+", "-", base).strip("-").strip()

    if not base:
        base = "loc"

    h = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:8]
    out = f"{base}-{h}"

    return out[:max_len]

KML_NS = {
    "kml": "http://www.opengis.net/kml/2.2",
    "gx": "http://www.google.com/kml/ext/2.2",
}


def _txt(el, path: str) -> str:
    e = el.find(path, KML_NS)
    if e is None or not e.text:
        return ""
    return (e.text or "").strip()


def _parse_coords(coord_text: str):
    pts = []
    for part in re.split(r"\s+", (coord_text or "").strip()):
        if not part:
            continue
        nums = part.split(",")
        if len(nums) >= 2:
            lon = float(nums[0])
            lat = float(nums[1])
            pts.append((lon, lat))
    return pts


def _centroid(pts):
    if not pts:
        return None
    lon = sum(p[0] for p in pts) / len(pts)
    lat = sum(p[1] for p in pts) / len(pts)
    return lat, lon


def _geom_from_placemark(pm):
    pt = pm.find(".//kml:Point/kml:coordinates", KML_NS)
    if pt is not None and pt.text:
        pts = _parse_coords(pt.text)
        if pts:
            lon, lat = pts[0]
            return "Point", lat, lon

    poly = pm.find(".//kml:Polygon//kml:coordinates", KML_NS)
    if poly is not None and poly.text:
        pts = _parse_coords(poly.text)
        c = _centroid(pts)
        if c:
            lat, lon = c
            return "Polygon", lat, lon

    line = pm.find(".//kml:LineString/kml:coordinates", KML_NS)
    if line is not None and line.text:
        pts = _parse_coords(line.text)
        c = _centroid(pts)
        if c:
            lat, lon = c
            return "LineString", lat, lon

    return "Unknown", None, None


def _iter_folders(parent_el, parent_path):
    for f in parent_el.findall("kml:Folder", KML_NS):
        name = _txt(f, "kml:name") or "Unnamed Folder"
        path = parent_path + [name]
        yield f, path
        yield from _iter_folders(f, path)


def _slug(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _location_exists(name: str) -> bool:
    return bool(frappe.db.exists("Location", name))


def _ensure_location(
    location_name: str,
    parent_docname: str,
    is_group: int,
    lat=None,
    lon=None,
    extra=None,
    dry_run: int = 1,
):
    # Keep the human label fairly intact, just normalize whitespace
    location_name = (location_name or "").strip()
    parent_docname = (parent_docname or "").strip()
    if not location_name:
        return None, "skip_blank"

    # If a Location already exists with this exact docname, reuse it.
    # reuse existing groups by exact name (Boschendal, buckets)
    if is_group and frappe.db.exists("Location", location_name):
        if not frappe.db.get_value("Location", location_name, "is_group"):
            frappe.throw(f"Location '{location_name}' exists but is not a group; cannot reuse as group.")
        return location_name, "exists"

    # ✅ choose docname
    if is_group:
        docname = _safe_docname(location_name)   # groups: readable-ish
    else:
        docname = _leaf_docname(parent_docname, location_name)  # leaves: pure hash

    # ✅ existence check by docname
    if frappe.db.exists("Location", docname):
        return docname, "exists"
    
    # ✅ enforce unique, human-readable location_name (Location has unique constraint here)
    if not is_group:
        location_name = _unique_location_name(location_name, docname)

    if dry_run:
        return docname, "create_dry"

    doc = frappe.get_doc({
        "doctype": "Location",
        "name": docname,
        "location_name": location_name,
        "parent_location": parent_docname or None,
        "is_group": 1 if is_group else 0,
    })
    doc.name = docname  # ✅ keep this too (belt + braces)

    if lat is not None:
        doc.latitude = lat
    if lon is not None:
        doc.longitude = lon

    if extra:
        meta = frappe.get_meta("Location")
        valid = set(meta.get_valid_columns() or [])
        for k, v in extra.items():
            if k in valid:
                setattr(doc, k, v)

    if not doc.name:
        frappe.throw(f"BUG: empty doc.name for Location '{location_name}' parent '{parent_docname}'")
       
    doc.insert(ignore_permissions=True, set_name=docname)
    
    return doc.name, "created"


def _bucket_for(folder_path: list[str], geom_type: str) -> str:
    # Map folder/layer names to stable buckets (sub-groups) under the site group
    # Keep this simple and adjustable.
    p0 = (folder_path[0] if folder_path else "").lower()
    p1 = (folder_path[1] if len(folder_path) > 1 else "").lower()

    if "building" in p0 or "building" in p1:
        return "Buildings"
    if "resident" in p0 or "resident" in p1 or "house" in p0 or "house" in p1:
        return "Residents"
    if "wireless" in p0 or "wifi" in p0 or "wireless" in p1 or "wifi" in p1:
        return "Network Nodes"
    if geom_type == "LineString":
        return "Links"
    if geom_type == "Polygon":
        return "Areas"
    return "Other"


def run(
    kmz_path: str,
    site_group: str,
    pilot_root: str = "Pilot Sites",
    dry_run: int = 1,
    commit: int = 0,
):
    """
    Import KMZ into Location tree:
      Pilot Sites -> <site_group> (group)
        -> Buckets (groups)
          -> Placemarks (leaf nodes)
    - dry_run=1 prints what would be created.
    - commit=1 actually writes and commits.
    """
    kmz_path = str(kmz_path)
    site_group = _slug(site_group)
    pilot_root = _slug(pilot_root)

    if not site_group:
        raise ValueError("site_group is required")

    if not frappe.db.exists("Location", pilot_root):
        raise ValueError(f"pilot_root Location '{pilot_root}' does not exist")

    dry_run = 1 if int(dry_run) else 0
    commit = 1 if int(commit) else 0
    if commit:
        dry_run = 0

    # Extract KMZ
    kmz = Path(kmz_path)
    if not kmz.exists():
        raise ValueError(f"KMZ not found: {kmz_path}")

    extract_dir = Path("/tmp/kmz_extract_import")
    extract_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(kmz, "r") as z:
        z.extractall(extract_dir)

    kml_file = extract_dir / "doc.kml"
    if not kml_file.exists():
        # sometimes it's named differently; find any .kml
        kmls = list(extract_dir.rglob("*.kml"))
        if not kmls:
            raise ValueError("No .kml found inside KMZ")
        kml_file = kmls[0]

    tree = ET.parse(str(kml_file))
    root = tree.getroot()
    doc = root.find("kml:Document", KML_NS)
    if doc is None:
        raise ValueError("Invalid KML: Document element not found")

    created = {"groups": 0, "leafs": 0, "exists": 0, "skipped": 0}
    buckets_created = set()

    # Ensure site group (group) under Pilot Sites
    pilot_root_dn = "Pilot Sites"  # Pilot Sites already exists, use its doc.name
    site_group_dn, status = _ensure_location(site_group, pilot_root_dn, is_group=1, dry_run=dry_run)
    if status in ("created", "create_dry"):
        created["groups"] += 1
    else:
        created["exists"] += 1

    # Collect placemarks from root + folders
    placemarks = []

    for pm in doc.findall("kml:Placemark", KML_NS):
        placemarks.append(([], pm))

    for folder, path in _iter_folders(doc, []):
        for pm in folder.findall("kml:Placemark", KML_NS):
            placemarks.append((path, pm))

    # Pre-create standard buckets (groups) to keep tree stable
    bucket_dns = {}
    for b in ("Buildings", "Residents", "Network Nodes", "Links", "Areas", "Other"):
        b_label = f"{site_group} - {b}"
        b_dn, st = _ensure_location(b_label, site_group_dn, is_group=1, dry_run=dry_run)
        bucket_dns[b] = b_dn

        if st in ("created", "create_dry"):
            created["groups"] += 1
        else:
            created["exists"] += 1

    # Import each placemark as a leaf under a bucket
    for folder_path, pm in placemarks:
        pname = _txt(pm, "kml:name") or "Unnamed"
        desc = _txt(pm, "kml:description")
        geom_type, lat, lon = _geom_from_placemark(pm)

        bucket = _bucket_for(folder_path, geom_type)

        # Buildings go directly under the Site Group docname (ticketable immediately)
        parent_dn = site_group_dn if bucket == "Buildings" else bucket_dns[bucket]

        # Leaf name: keep original, but prefix with bucket for safety if duplicates might exist
        leaf_name = f"{bucket}: {pname}".strip()

        extra = {
            "custom_kmz_source": kmz.name,
            "custom_kmz_folder_path": f"{site_group} / " + " / ".join(folder_path) if folder_path else site_group,
            "custom_kmz_geometry_type": geom_type,   # <- match your fieldname
            "custom_kmz_description": (desc or "")[:2000],
        }

        nm, st = _ensure_location(
            leaf_name,
            parent_dn,
            is_group=0,
            lat=lat,
            lon=lon,
            extra=extra,
            dry_run=dry_run,
        )

        if st == "skip_blank":
            created["skipped"] += 1
        elif st in ("created", "create_dry"):
            created["leafs"] += 1
        else:
            created["exists"] += 1

    if commit:
        frappe.db.commit()

    print("KMZ import complete")
    print("site_group:", site_group)
    print("dry_run:", dry_run, "commit:", commit)
    print("counts:", created)
    print("total_placemarks:", len(placemarks))
    return created
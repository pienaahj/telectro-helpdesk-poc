console.log("telectro_location_map_zoom.js loaded");

frappe.ui.form.on("Location", {
  refresh(frm) {
    setTimeout(() => {
      zoom_telectro_point_location_map(frm);
    }, 700);

    setTimeout(() => {
      zoom_telectro_point_location_map(frm);
    }, 1500);
  },
});

function zoom_telectro_point_location_map(frm) {
  if (!frm || frm.doctype !== "Location") {
    return;
  }

  const lat = Number(frm.doc.latitude);
  const lng = Number(frm.doc.longitude);

  if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
    return;
  }

  const geometryType = (frm.doc.custom_kmz_geometry_type || "").trim();

  // Be conservative: only force high zoom for point-style locations.
  // Boschendal campus itself currently also says Point, but the real value is
  // leaf asset/fault locations. This still keeps non-point future geometry safe.
  if (geometryType && geometryType !== "Point") {
    return;
  }

  const control = frm.fields_dict?.location;

  if (!control) {
    console.warn(
      "[telectro_location_map_zoom] Location.location control not found",
    );
    return;
  }

  const map = get_leaflet_map_from_geolocation_control(control);

  if (!map || typeof map.setView !== "function") {
    console.warn(
      "[telectro_location_map_zoom] Leaflet map instance not ready/found",
      control,
    );
    return;
  }

  map.setView([lat, lng], 19);
}

function get_leaflet_map_from_geolocation_control(control) {
  const candidates = [
    control.map,
    control.map_area?.map,
    control.map_area?.leaflet_map,
    control.location_map,
    control.leaflet_map,
    control.$wrapper?.data?.("map"),
  ];

  for (const candidate of candidates) {
    if (candidate && typeof candidate.setView === "function") {
      return candidate;
    }
  }

  // Last-resort recursive scan, limited so we do not wander the whole world.
  return find_leaflet_map_candidate(control, 0, new Set());
}

function find_leaflet_map_candidate(value, depth, seen) {
  if (!value || depth > 3) {
    return null;
  }

  if (typeof value !== "object") {
    return null;
  }

  if (seen.has(value)) {
    return null;
  }

  seen.add(value);

  if (
    typeof value.setView === "function" &&
    typeof value.getZoom === "function"
  ) {
    return value;
  }

  for (const key of Object.keys(value)) {
    if (
      key.startsWith("_") ||
      ["doc", "frm", "df", "$wrapper", "wrapper"].includes(key)
    ) {
      continue;
    }

    const found = find_leaflet_map_candidate(value[key], depth + 1, seen);

    if (found) {
      return found;
    }
  }

  return null;
}

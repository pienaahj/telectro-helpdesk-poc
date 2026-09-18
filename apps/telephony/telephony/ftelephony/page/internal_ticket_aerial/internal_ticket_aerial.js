frappe.pages["internal-ticket-aerial"].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: "Ticket Aerial View",
    single_column: true,
  });

  const $body = $(wrapper).find(".layout-main-section");

  let map = null;

  function getTicketName() {
    const route = frappe.get_route() || [];
    return route[1] || "";
  }

  function destroyMap() {
    if (!map) {
      return;
    }

    map.remove();
    map = null;
  }

  function escapeHtml(value) {
    return frappe.utils.escape_html(
      value === null || value === undefined || value === ""
        ? "—"
        : String(value),
    );
  }

  function buildRow(label, value) {
    return `
      <div class="text-muted small">${escapeHtml(label)}</div>
      <div>${escapeHtml(value)}</div>
    `;
  }

  function renderShell(ticketName) {
    destroyMap();
    $body.empty();

    $body.append(`
      <div class="telectro-internal-aerial-page">
        <div
          class="d-flex justify-content-between align-items-start mb-4"
          style="gap: 12px;"
        >
          <div>
            <div class="text-muted small text-uppercase">
              Internal ticket location
            </div>
            <h3 class="mb-1">
              Aerial view
            </h3>
            <div class="text-muted">
              HD Ticket #${escapeHtml(ticketName)}
            </div>
          </div>

          <a
            class="btn btn-default btn-sm"
            href="/app/hd-ticket/${encodeURIComponent(ticketName)}"
          >
            Back to HD Ticket
          </a>
        </div>

        <div
          id="ita-error"
          class="alert alert-danger"
          style="display:none;"
        ></div>

        <div
          id="ita-loading"
          class="text-muted"
        >
          Loading ticket location…
        </div>

        <div
          id="ita-content"
          style="display:none;"
        >
          <div
            id="ita-context"
            style="
              display: grid;
              grid-template-columns: minmax(140px, 190px) 1fr;
              gap: 8px 16px;
              padding: 16px;
              margin-bottom: 16px;
              border: 1px solid var(--border-color);
              border-radius: 8px;
              background: var(--card-bg);
            "
          ></div>

          <div
            id="ita-map"
            style="
              width: 100%;
              height: min(65vh, 620px);
              min-height: 420px;
              border: 1px solid var(--border-color);
              border-radius: 8px;
              overflow: hidden;
            "
          ></div>

          <div
            id="ita-no-map"
            class="text-muted"
            style="
              display:none;
              padding: 24px;
              text-align: center;
              border: 1px dashed var(--border-color);
              border-radius: 8px;
            "
          >
            No map coordinates are available for this fault location.
          </div>
        </div>
      </div>
    `);
  }

  function showError(message) {
    $body.find("#ita-loading").hide();
    $body.find("#ita-content").hide();

    $body
      .find("#ita-error")
      .text(message || "Unable to load this ticket location.")
      .show();
  }

  function renderContext(context) {
    const campus = context.campus || {};
    const faultPoint = context.fault_point || {};
    const faultAsset = context.fault_asset || {};
    const equipment = context.affected_equipment || {};
    const primary = context.primary_location || {};

    const rows = [
      ["Customer", context.customer],
      ["Campus", campus.label],
      ["Category", context.category],
      ["Fault Point", faultPoint.label],
    ];

    if (
      faultAsset.id &&
      faultAsset.id !== faultPoint.id
    ) {
      rows.push([
        "Fault Asset",
        faultAsset.label,
      ]);
    }

    rows.push(
      [
        "Affected Equipment",
        equipment.label,
      ],
      [
        "Equipment / Circuit / SIM / Tag",
        context.equipment_ref,
      ],
      [
        "Latitude",
        primary.latitude,
      ],
      [
        "Longitude",
        primary.longitude,
      ],
    );

    $body
      .find("#ita-context")
      .html(
        rows
          .map(([label, value]) =>
            buildRow(label, value),
          )
          .join(""),
      );
  }

  function renderMap(context) {
    destroyMap();

    const primary = context.primary_location || {};
    const aerial = context.aerial || {};

    const latitude = Number(primary.latitude);
    const longitude = Number(primary.longitude);

    if (
      !Number.isFinite(latitude) ||
      !Number.isFinite(longitude)
    ) {
      $body.find("#ita-map").hide();
      $body.find("#ita-no-map").show();
      return;
    }

    if (
      !aerial.configured ||
      !aerial.api_key ||
      !aerial.tile_url
    ) {
      showError(
        "Aerial map configuration is unavailable.",
      );
      return;
    }

    if (
      typeof window.L !== "object" ||
      typeof window.L.map !== "function"
    ) {
      showError(
        "Map support is unavailable in this Desk session.",
      );
      return;
    }

    const mapElement = $body.find("#ita-map")[0];

    if (!mapElement) {
      showError(
        "Map container is unavailable.",
      );
      return;
    }

    $body.find("#ita-no-map").hide();
    $body.find("#ita-map").show();

    map = window.L
      .map(mapElement)
      .setView(
        [latitude, longitude],
        19,
      );

    const tileUrl =
      `${aerial.tile_url}` +
      `?token=${encodeURIComponent(aerial.api_key)}`;

    window.L
      .tileLayer(
        tileUrl,
        {
          attribution: aerial.attribution || "",
        },
      )
      .addTo(map);

    window.L
      .circleMarker(
        [latitude, longitude],
      )
      .addTo(map)
      .bindTooltip(
        escapeHtml(
          primary.label || "Fault Location",
        ),
      );

    setTimeout(() => {
      map?.invalidateSize();
    }, 0);
  }

  function renderContextAndMap(context) {
    $body.find("#ita-error").hide();
    $body.find("#ita-loading").hide();
    $body.find("#ita-content").show();

    renderContext(context);
    renderMap(context);
  }

  function loadTicket() {
    const ticketName = getTicketName();

    if (!ticketName) {
      renderShell("");
      showError(
        "A ticket is required.",
      );
      return;
    }

    renderShell(ticketName);

    frappe.call({
      method:
        "telephony.api.workspace.internal_ticket_aerial_context",
      args: {
        ticket_name: ticketName,
      },
      callback(r) {
        const context = r.message || {};

        if (!context.ok) {
          showError(
            context.reason ||
              "Unable to load this ticket location.",
          );
          return;
        }

        renderContextAndMap(context);
      },
      error(error) {
        console.error(
          "[internal-ticket-aerial] load failed",
          error,
        );

        showError(
          "Unable to load this ticket location.",
        );
      },
    });
  }

  wrapper.internal_ticket_aerial_page = {
    loadTicket,
    destroyMap,
  };

  loadTicket();
};

frappe.pages["internal-ticket-aerial"].on_page_show = function (wrapper) {
  wrapper.internal_ticket_aerial_page?.loadTicket?.();
};

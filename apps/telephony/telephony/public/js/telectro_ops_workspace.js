(function () {
  const MOUNT_SELECTOR =
    '#telectro-stale-unclaimed-widget, [data-telectro-widget="stale-unclaimed"]';

  console.log("[telectro_ops_workspace] loaded");

  function findInShadowRoots(selector) {
    const nodes = document.querySelectorAll("*");
    for (const node of nodes) {
      if (node.shadowRoot) {
        const found = node.shadowRoot.querySelector(selector);
        if (found) return found;
      }
    }
    return null;
  }

  function getMount() {
    return (
      document.querySelector(MOUNT_SELECTOR) ||
      findInShadowRoots(MOUNT_SELECTOR)
    );
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function renderLoading(mount) {
    mount.innerHTML = `
      <div class="widget quick-list-widget-box">
        <div class="widget-head">
          <div class="widget-label">
            <div class="widget-title">
              <span class="ellipsis" title="Unclaimed > 1 Day">Unclaimed > 1 Day</span>
            </div>
          </div>
        </div>
        <div class="widget-body">
          <div class="list-loading-state text-muted">Loading...</div>
        </div>
        <div class="widget-footer">
          <div class="see-all btn btn-xs">View List</div>
        </div>
      </div>
    `;
  }

  function bindViewList(mount, reportRoute) {
    const btn = mount.querySelector(".see-all");
    if (!btn) return;

    btn.addEventListener("click", function (e) {
      if (e.ctrlKey || e.metaKey) {
        frappe.open_in_new_tab = true;
      }
      frappe.set_route(
        (reportRoute || "/app/query-report/Unclaimed%20Over%201%20Day").replace(
          /^\/app\//,
          "",
        ),
      );
    });
  }

  function renderEmpty(mount, payload) {
    mount.innerHTML = `
      <div class="widget quick-list-widget-box">
        <div class="widget-head">
          <div class="widget-label">
            <div class="widget-title">
              <span class="ellipsis" title="${escapeHtml(payload.title || "Unclaimed > 1 Day")}">
                ${escapeHtml(payload.title || "Unclaimed > 1 Day")}
              </span>
            </div>
          </div>
        </div>
        <div class="widget-body">
          <div class="list-no-data-state text-muted">No Data...</div>
        </div>
        <div class="widget-footer">
          <div class="see-all btn btn-xs">View List</div>
        </div>
      </div>
    `;
    bindViewList(mount, payload.report_route);
  }

  function renderCard(mount, payload) {
    const rows = payload.rows || [];
    const rowsHtml = rows
      .map((row) => {
        const statusClass =
          (row.status || "").toLowerCase() === "open" ? "red" : "blue";
        return `
          <div class="quick-list-item telectro-stale-unclaimed-row" data-route="${escapeHtml(row.route)}">
            <div class="ellipsis left">
              <div class="ellipsis title" title="${escapeHtml(row.subject)}">
                ${escapeHtml(row.subject)}
              </div>
              <div class="timestamp text-muted">
                ${escapeHtml(row.modified_pretty)} · ${escapeHtml(row.idle_hours)}h idle
              </div>
            </div>
            <div class="status indicator-pill ${statusClass} ellipsis">
              ${escapeHtml(row.status)}
            </div>
            <div class="right-arrow">${frappe.utils.icon("right", "xs")}</div>
          </div>
        `;
      })
      .join("");

    mount.innerHTML = `
      <div class="widget quick-list-widget-box">
        <div class="widget-head">
          <div class="widget-label">
            <div class="widget-title">
              <span class="ellipsis" title="${escapeHtml(payload.title || "Unclaimed > 1 Day")}">
                ${escapeHtml(payload.title || "Unclaimed > 1 Day")}
              </span>
            </div>
          </div>
        </div>
        <div class="widget-body">
          ${rowsHtml || '<div class="list-no-data-state text-muted">No Data...</div>'}
        </div>
        <div class="widget-footer">
          <div class="see-all btn btn-xs">View List</div>
        </div>
      </div>
    `;

    mount.querySelectorAll(".telectro-stale-unclaimed-row").forEach((el) => {
      el.addEventListener("click", function (e) {
        const route = el.getAttribute("data-route");
        if (!route) return;
        if (e.ctrlKey || e.metaKey) {
          frappe.open_in_new_tab = true;
        }
        frappe.set_route(route.replace(/^\/app\//, ""));
      });
    });

    bindViewList(mount, payload.report_route);
  }

  async function loadCard() {
    console.log("[telectro_ops_workspace] loadCard called");

    const mount = getMount();
    console.log("[telectro_ops_workspace] mount =", mount);

    if (!mount) return;

    renderLoading(mount);

    try {
      const r = await frappe.call({
        method: "telephony.api.workspace.unclaimed_over_1_day_card",
        args: { limit: 4 },
      });

      console.log("[telectro_ops_workspace] response=", r);

      const payload = r.message || {};
      if (!payload.rows || !payload.rows.length) {
        renderEmpty(mount, payload);
      } else {
        renderCard(mount, payload);
      }
    } catch (e) {
      console.error(
        "[telectro_ops_workspace] failed to load stale unclaimed card",
        e,
      );
      mount.innerHTML = '<div class="text-danger">Unable to load...</div>';
    }
  }

  document.addEventListener("DOMContentLoaded", loadCard);
  $(document).on("page-change", function () {
    setTimeout(loadCard, 300);
    setTimeout(loadCard, 1000);
  });
  setTimeout(loadCard, 1500);
  setTimeout(loadCard, 3000);
})();

(function () {
  const MOUNT_SELECTOR =
    '#telectro-stale-unclaimed-widget, [data-telectro-widget="stale-unclaimed"]';

  function openCoordinatorUpliftDialog() {
    frappe
      .call({
        method: "telephony.api.workspace.coordinator_uplift_candidates",
      })
      .then((r) => {
        const payload = r.message || {};
        const rows = payload.rows || [];

        if (!rows.length) {
          frappe.msgprint("No valid coordinator uplift candidates found.");
          return;
        }

        const byName = {};
        rows.forEach((row) => {
          byName[row.name] = row;
        });

        const initialUser = rows[0].name;

        const d = new frappe.ui.Dialog({
          title: "Manage Coordinator Uplift",
          fields: [
            {
              fieldname: "user_email",
              fieldtype: "Select",
              label: "User",
              options: rows.map((row) => row.name).join("\n"),
              reqd: 1,
              default: initialUser,
            },
            {
              fieldname: "display_name",
              fieldtype: "Data",
              label: "Full Name",
              read_only: 1,
            },
            {
              fieldname: "current_state",
              fieldtype: "Data",
              label: "Current State",
              read_only: 1,
            },
            {
              fieldname: "current_profile",
              fieldtype: "Data",
              label: "Current Profile",
              read_only: 1,
            },
          ],
        });

        function submitAction() {
          const values = d.get_values();
          if (!values) return;

          const selected = byName[values.user_email];
          if (!selected) {
            frappe.msgprint("Please choose a valid user.");
            return;
          }

          const currentState = d.get_value("current_state");
          const isCoordinator = currentState === "Coordinator active";

          const method = isCoordinator
            ? "telephony.api.workspace.revoke_coordinator_uplift"
            : "telephony.api.workspace.grant_coordinator_uplift";

          frappe
            .call({
              method,
              args: { user_email: selected.name },
              freeze: true,
              freeze_message: isCoordinator
                ? "Revoking coordinator uplift..."
                : "Granting coordinator uplift...",
            })
            .then((res) => {
              const msg = res.message || {};

              if (msg.user && byName[msg.user]) {
                byName[msg.user] = {
                  ...byName[msg.user],
                  name: msg.user,
                  email: msg.user,
                  full_name: msg.full_name,
                  enabled: msg.enabled,
                  role_profile_name: msg.role_profile_name,
                  is_coordinator_uplifted: msg.is_coordinator_uplifted,
                  status_label: msg.is_coordinator_uplifted
                    ? "Coordinator active"
                    : "Technician only",
                };
              }

              frappe.show_alert({
                message: msg.message || "Coordinator uplift updated.",
                indicator: "green",
              });

              d.hide();
              setTimeout(loadCurrentCoordinatorCard, 200);
              setTimeout(loadCurrentCoordinatorCard, 800);
            })
            .catch((err) => {
              console.error(
                "[telectro_ops_workspace] coordinator uplift action failed",
                err,
              );
              frappe.msgprint("Unable to update coordinator uplift.");
            });
        }

        function setState(row) {
          d.set_value("display_name", row?.full_name || "");
          d.set_value("current_state", row?.status_label || "");
          d.set_value("current_profile", row?.role_profile_name || "");

          d.set_primary_action(
            row && row.is_coordinator_uplifted
              ? "Revoke Coordinator"
              : "Grant Coordinator",
            submitAction,
          );
        }

        d.fields_dict.user_email.$input.on("change", function () {
          const selectedUser = d.get_value("user_email");
          setState(byName[selectedUser]);
        });

        d.show();
        setState(byName[initialUser]);
      })
      .catch((err) => {
        console.error(
          "[telectro_ops_workspace] failed to load coordinator uplift candidates",
          err,
        );
        frappe.msgprint("Unable to load coordinator uplift candidates.");
      });
  }

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
          <div class="see-all btn btn-xs">View Full List</div>
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
          <div class="see-all btn btn-xs">View Full List</div>
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
          <div class="see-all btn btn-xs">View Full List</div>
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

  function renderCoordinatorLoading(mount) {
    mount.innerHTML = `
            <div class="widget quick-list-widget-box">
            <div class="widget-head">
                <div class="widget-label">
                <div class="widget-title">
                    <span class="ellipsis" title="Current Coordinator Uplift">Current Coordinator Uplift</span>
                </div>
                </div>
            </div>
            <div class="widget-body">
                <div class="list-loading-state text-muted">Loading...</div>
            </div>
            <div class="widget-footer">
                <div class="see-all btn btn-xs">View Full List</div>
            </div>
            </div>
        `;
  }

  function bindCoordinatorViewList(mount, reportRoute) {
    const btn = mount.querySelector(".see-all");
    if (!btn) return;

    btn.addEventListener("click", function (e) {
      if (e.ctrlKey || e.metaKey) {
        frappe.open_in_new_tab = true;
      }
      frappe.set_route(
        (
          reportRoute || "/app/query-report/Current%20Coordinator%20Uplift"
        ).replace(/^\/app\//, ""),
      );
    });
  }

  function renderCoordinatorEmpty(mount, payload) {
    mount.innerHTML = `
          <div class="widget quick-list-widget-box">
          <div class="widget-head">
              <div class="widget-label">
              <div class="widget-title">
                  <span class="ellipsis" title="${escapeHtml(payload.title || "Current Coordinator Uplift")}">
                  ${escapeHtml(payload.title || "Current Coordinator Uplift")}
                  </span>
              </div>
              </div>
          </div>
          <div class="widget-body">
              <div class="list-no-data-state text-muted">None assigned</div>
          </div>
          <div class="widget-footer">
              <div class="see-all btn btn-xs">View Full List</div>
          </div>
          </div>
      `;
    bindCoordinatorViewList(mount, payload.report_route);
  }

  function renderCoordinatorCard(mount, payload) {
    const rows = payload.rows || [];
    const rowsHtml = rows
      .map((row) => {
        const enabledClass = row.enabled ? "green" : "red";
        const enabledLabel = row.enabled ? "Enabled" : "Disabled";

        return `
          <div class="quick-list-item telectro-current-coordinator-row">
            <div class="ellipsis left">
              <div class="ellipsis title" title="${escapeHtml(row.full_name)}">
                ${escapeHtml(row.full_name)}
              </div>
              <div class="timestamp text-muted">
                ${escapeHtml(row.email)}${row.modified_pretty ? ` · ${escapeHtml(row.modified_pretty)}` : ""}
              </div>
            </div>
            <div class="status indicator-pill ${enabledClass} ellipsis">
              ${escapeHtml(enabledLabel)}
            </div>
          </div>
        `;
      })
      .join("");

    mount.innerHTML = `
      <div class="widget quick-list-widget-box">
        <div class="widget-head">
          <div class="widget-label">
            <div class="widget-title">
              <span class="ellipsis" title="${escapeHtml(payload.title || "Current Coordinator Uplift")}">
                ${escapeHtml(payload.title || "Current Coordinator Uplift")}
              </span>
            </div>
          </div>
        </div>
        <div class="widget-body">
          ${rowsHtml || '<div class="list-no-data-state text-muted">None assigned</div>'}
        </div>
        <div class="widget-footer">
          <div class="see-all btn btn-xs">View Full List</div>
        </div>
      </div>
    `;

    bindCoordinatorViewList(mount, payload.report_route);
  }

  async function loadCurrentCoordinatorCard() {
    const selector =
      '#telectro-current-coordinator-widget, [data-telectro-widget="current-coordinator"]';

    const mount =
      document.querySelector(selector) || findInShadowRoots(selector);

    if (!mount) return;

    renderCoordinatorLoading(mount);

    try {
      const r = await frappe.call({
        method: "telephony.api.workspace.current_coordinator_uplift_card",
        args: { limit: 10 },
      });

      const payload = r.message || {};
      if (!payload.rows || !payload.rows.length) {
        renderCoordinatorEmpty(mount, payload);
      } else {
        renderCoordinatorCard(mount, payload);
      }
    } catch (e) {
      console.error(
        "[telectro_ops_workspace] failed to load current coordinator card",
        e,
      );
      mount.innerHTML = '<div class="text-danger">Unable to load...</div>';
    }
  }

  async function loadCard() {
    const mount = getMount();
    if (!mount) return;

    renderLoading(mount);

    try {
      const r = await frappe.call({
        method: "telephony.api.workspace.unclaimed_over_1_day_card",
        args: { limit: 4 },
      });

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

  document.addEventListener("DOMContentLoaded", function () {
    loadCard();
    loadCurrentCoordinatorCard();
  });

  $(document).on("page-change", function () {
    setTimeout(loadCard, 300);
    setTimeout(loadCard, 1000);
    setTimeout(loadCurrentCoordinatorCard, 300);
    setTimeout(loadCurrentCoordinatorCard, 1000);
  });

  setTimeout(loadCard, 1500);
  setTimeout(loadCard, 3000);
  setTimeout(loadCurrentCoordinatorCard, 1500);
  setTimeout(loadCurrentCoordinatorCard, 3000);
  window.openCoordinatorUpliftDialog = openCoordinatorUpliftDialog;
})();

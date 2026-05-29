console.log("telectro_handoff_action.js loaded");

frappe.ui.form.on("HD Ticket", {
  refresh(frm) {
    setTimeout(() => {
      hide_split_and_merge_section(frm);
      add_controlled_handoff_action(frm);
      add_share_ticket_context_action(frm);
      render_internal_fault_location_context(frm);
    }, 300);
  },

  onload_post_render(frm) {
    hide_split_and_merge_section(frm);
  },
});

function add_controlled_handoff_action(frm) {
  if (!should_show_controlled_handoff(frm)) {
    return;
  }

  if (has_custom_button(frm, "Controlled Handoff")) {
    return;
  }

  frm.add_custom_button("Controlled Handoff", () => {
    open_controlled_handoff_dialog(frm);
  });
}

async function open_controlled_handoff_dialog(frm) {
  const assignmentState = await get_current_assignment_state(frm.doc.name);
  const currentOwner = assignmentState.current_owner || "";

  const dialog = new frappe.ui.Dialog({
    title: "Controlled Handoff",
    fields: [
      {
        label: "Current Accountable Owner",
        fieldname: "current_owner",
        fieldtype: "Data",
        read_only: 1,
        default: currentOwner || "Pool / Unassigned",
      },
      {
        label: "New Accountable Owner",
        fieldname: "to_user",
        fieldtype: "Link",
        options: "User",
        reqd: 1,
        get_query() {
          return {
            filters: {
              enabled: 1,
              user_type: "System User",
            },
          };
        },
      },
      {
        label: "Reason",
        fieldname: "reason",
        fieldtype: "Small Text",
        reqd: 1,
        description:
          "Required. This is written to the ticket timeline as the handoff reason.",
      },
    ],
    primary_action_label: "Handoff",
    primary_action(values) {
      if (!values.to_user) {
        frappe.msgprint("Please select the new accountable owner.");
        return;
      }

      if (!values.reason || !values.reason.trim()) {
        frappe.msgprint("Please enter a handoff reason.");
        return;
      }

      frappe.call({
        method: "telephony.telectro_claim.telectro_handoff_ticket",
        args: {
          ticket: frm.doc.name,
          to_user: values.to_user,
          reason: values.reason,
        },
        freeze: true,
        freeze_message: "Applying controlled handoff...",
        callback(r) {
          const msg = r.message || {};

          if (!msg.ok) {
            frappe.msgprint({
              title: __("Handoff not applied"),
              message: __("Reason: {0}", [msg.reason || "Unknown"]),
              indicator: "orange",
            });
            return;
          }

          frappe.show_alert({
            message: __("Ticket handed off to {0}", [msg.to]),
            indicator: "green",
          });

          dialog.hide();
          frm.reload_doc();
        },
        error(xhr) {
          console.error("[telectro_handoff_action] handoff failed", xhr);
          frappe.msgprint({
            title: __("Handoff failed"),
            message: __("Could not apply controlled handoff."),
            indicator: "red",
          });
        },
      });
    },
  });

  dialog.show();
}

async function get_current_assignment_state(ticketName) {
  try {
    const r = await frappe.call({
      method: "telephony.telectro_claim.telectro_ticket_assignment_state",
      args: {
        ticket: ticketName,
      },
    });

    return r.message || {};
  } catch (e) {
    console.error(
      "[telectro_handoff_action] failed to load assignment state",
      e,
    );

    frappe.show_alert({
      message: "Unable to load current assignment state.",
      indicator: "orange",
    });

    return {
      ok: 0,
      current_owner: "",
      effective_users: [],
      is_pool: true,
    };
  }
}

function should_show_controlled_handoff(frm) {
  const d = frm.doc || {};

  if (!d.name || frm.is_new()) {
    return false;
  }

  if (d.doctype !== "HD Ticket") {
    return false;
  }

  if (!has_handoff_role()) {
    return false;
  }

  if (["Resolved", "Closed", "Archived"].includes(d.status || "")) {
    return false;
  }

  // Partner fulfilment tickets should stay on the Partner flow.
  if ((d.custom_fulfilment_party || "").trim() === "Partner") {
    return false;
  }

  return true;
}

function has_handoff_role() {
  return [
    "System Manager",
    "Pilot Admin",
    "TELECTRO-POC Role - Supervisor Governance",
    "TELECTRO-POC Role - Coordinator Ops",
  ].some((role) => frappe.user.has_role(role));
}

function get_current_accountable_owner(frm) {
  const raw = frm.doc?._assign;

  if (!raw) {
    return "";
  }

  if (Array.isArray(raw)) {
    return raw.filter(Boolean).join(", ");
  }

  if (typeof raw === "string") {
    const trimmed = raw.trim();
    if (!trimmed || trimmed === "[]") {
      return "";
    }

    try {
      const parsed = JSON.parse(trimmed);
      if (Array.isArray(parsed)) {
        return parsed.filter(Boolean).join(", ");
      }
    } catch (e) {
      return trimmed;
    }

    return trimmed;
  }

  return "";
}

function has_custom_button(frm, label) {
  return !!frm.custom_buttons?.[label];
}

function add_share_ticket_context_action(frm) {
  if (!should_show_share_ticket_context(frm)) {
    return;
  }

  if (has_custom_button(frm, "Share Ticket Context")) {
    return;
  }

  frm.add_custom_button("Share Ticket Context", () => {
    open_share_ticket_context_dialog(frm);
  });
}

function open_share_ticket_context_dialog(frm) {
  const currentOwner =
    get_current_accountable_owner(frm) || "Pool / Unassigned";

  const dialog = new frappe.ui.Dialog({
    title: "Share Ticket Context",
    fields: [
      {
        label: "Current Accountable Owner",
        fieldname: "current_owner",
        fieldtype: "Data",
        read_only: 1,
        default: currentOwner,
      },
      {
        label: "Collaborator",
        fieldname: "collaborator",
        fieldtype: "Link",
        options: "User",
        reqd: 1,
        get_query() {
          return {
            filters: {
              enabled: 1,
              user_type: "System User",
            },
          };
        },
      },
      {
        label: "Note / Reason",
        fieldname: "note",
        fieldtype: "Small Text",
        reqd: 1,
        description:
          "Required. This is written to the ticket timeline without changing assignment.",
      },
    ],
    primary_action_label: "Share Context",
    primary_action(values) {
      if (!values.collaborator) {
        frappe.msgprint("Please select a collaborator.");
        return;
      }

      if (!values.note || !values.note.trim()) {
        frappe.msgprint("Please enter a note / reason.");
        return;
      }

      frappe.call({
        method: "telephony.api.workspace.share_ticket_context",
        args: {
          ticket_name: frm.doc.name,
          collaborator: values.collaborator,
          note: values.note,
        },
        freeze: true,
        freeze_message: "Sharing ticket context...",
        callback(r) {
          const msg = r.message || {};

          if (!msg.ok) {
            frappe.msgprint({
              title: __("Context not shared"),
              message: __("Reason: {0}", [msg.reason || "Unknown"]),
              indicator: "orange",
            });
            return;
          }

          frappe.show_alert({
            message: __("Ticket context shared with {0}", [
              msg.collaborator_name || msg.collaborator,
            ]),
            indicator: "green",
          });

          dialog.hide();
          frm.reload_doc();
        },
        error(xhr) {
          console.error("[telectro_handoff_action] context share failed", xhr);
          frappe.msgprint({
            title: __("Context share failed"),
            message: __("Could not share ticket context."),
            indicator: "red",
          });
        },
      });
    },
  });

  dialog.show();
}

function should_show_share_ticket_context(frm) {
  const d = frm.doc || {};

  if (!d.name || frm.is_new()) {
    return false;
  }

  if (d.doctype !== "HD Ticket") {
    return false;
  }

  if (["Resolved", "Closed", "Archived"].includes(d.status || "")) {
    return false;
  }

  return (
    has_share_ticket_context_role() || is_current_user_accountable_owner(frm)
  );
}

function has_share_ticket_context_role() {
  return [
    "System Manager",
    "Pilot Admin",
    "TELECTRO-POC Role - Supervisor Governance",
    "TELECTRO-POC Role - Coordinator Ops",
  ].some((role) => frappe.user.has_role(role));
}

function is_current_user_accountable_owner(frm) {
  const currentOwner = get_current_accountable_owner(frm);
  const currentUser = frappe.session.user;

  if (!currentOwner || !currentUser) {
    return false;
  }

  return currentOwner
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean)
    .includes(currentUser);
}

function hide_split_and_merge_section(frm) {
  const fields = [
    "split_and_merge_section",
    "is_merged",
    "merged_with",
    "ticket_split_from",
  ];

  fields.forEach((fieldname) => {
    if (frm.fields_dict[fieldname]) {
      frm.set_df_property(fieldname, "hidden", 1);
    }
  });

  // Fallback for already-rendered section remnants.
  setTimeout(() => {
    $(".form-section .section-head")
      .filter((_, el) => (el.innerText || "").trim() === "Split and Merge")
      .closest(".form-section")
      .hide();
  }, 100);
}

async function render_internal_fault_location_context(frm) {
  if (!should_show_internal_fault_location_context(frm)) {
    remove_internal_fault_location_context(frm);
    return;
  }

  try {
    const wrapper = get_or_create_internal_fault_location_wrapper(frm);

    wrapper.html(`
      <div class="text-muted small">
        Loading fault location context...
      </div>
    `);

    const r = await frappe.call({
      method: "telephony.api.workspace.internal_ticket_location_context",
      args: {
        ticket_name: frm.doc.name,
      },
    });

    const ctx = r.message || {};

    if (!ctx.ok || !ctx.has_location_context) {
      remove_internal_fault_location_context(frm);
      return;
    }

    wrapper.html(build_internal_fault_location_html(ctx));
  } catch (e) {
    console.error(
      "[telectro_handoff_action] failed to load fault location context",
      e,
    );

    frappe.show_alert({
      message: "Fault location context could not be loaded.",
      indicator: "orange",
    });
  }
}

function should_show_internal_fault_location_context(frm) {
  const d = frm.doc || {};

  if (!d.name || frm.is_new()) {
    return false;
  }

  if (d.doctype !== "HD Ticket") {
    return false;
  }

  return !!(
    d.custom_site_group ||
    d.custom_site ||
    d.custom_fault_asset ||
    d.custom_equipment_ref
  );
}

function get_or_create_internal_fault_location_wrapper(frm) {
  const wrapperId = "telectro-internal-fault-location-context";
  const formWrapper = $(frm.wrapper || document);

  let wrapper = formWrapper.find(`#${wrapperId}`);

  if (wrapper.length) {
    return wrapper;
  }

  const html = `
    <div class="form-dashboard-section telectro-fault-location-section">
      <div class="section-head">
        ${__("Fault Location")}
      </div>
      <div class="section-body">
        <div id="${wrapperId}" class="telectro-internal-fault-location-context"></div>
      </div>
    </div>
  `;

  const dashboardArea = formWrapper.find(".form-dashboard").first();

  if (dashboardArea.length) {
    dashboardArea.append(html);
  } else {
    const layoutArea = formWrapper.find(".form-layout").first();

    if (layoutArea.length) {
      layoutArea.prepend(html);
    } else {
      formWrapper.prepend(html);
    }
  }

  return formWrapper.find(`#${wrapperId}`);
}

function remove_internal_fault_location_context(frm) {
  const wrapperId = "telectro-internal-fault-location-context";
  const formWrapper = $(frm.wrapper || document);
  const wrapper = formWrapper.find(`#${wrapperId}`);

  if (!wrapper.length) {
    return;
  }

  const section = wrapper.closest(".telectro-fault-location-section");

  if (section.length) {
    section.remove();
  } else {
    wrapper.remove();
  }
}

function build_internal_fault_location_html(ctx) {
  const primary = ctx.primary_location || ctx.fault_point || ctx.fault_asset;
  const campus = ctx.campus || {};
  const faultPoint = ctx.fault_point || {};
  const faultAsset = ctx.fault_asset || {};
  const showFaultAsset = faultAsset.id && faultAsset.id !== faultPoint.id;

  const rows = [
    build_context_row("Campus", campus.label, campus.route),
    build_context_row("Category", ctx.category),
    build_context_row("Fault Point", faultPoint.label, faultPoint.route),
  ];

  if (showFaultAsset) {
    rows.push(
      build_context_row("Fault Asset", faultAsset.label, faultAsset.route),
    );
  }

  rows.push(
    build_context_row(
      "Equipment / Circuit / SIM / Tag",
      ctx.equipment_ref || "",
    ),
  );

  const actions = build_internal_fault_location_actions(primary);

  return `
    <div class="telectro-fault-location-card" style="
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 12px;
      margin-bottom: 8px;
      background: var(--card-bg);
    ">
      <div style="
        display: grid;
        grid-template-columns: minmax(130px, 180px) 1fr;
        gap: 6px 12px;
        align-items: start;
      ">
        ${rows.join("")}
      </div>

      ${actions}
    </div>
  `;
}

function build_context_row(label, value, route) {
  const safeLabel = frappe.utils.escape_html(label || "");
  const safeValue = frappe.utils.escape_html(value || "-");

  let renderedValue = safeValue;

  if (route && value) {
    const safeRoute = frappe.utils.escape_html(route);
    renderedValue = `<a href="${safeRoute}">${safeValue}</a>`;
  }

  return `
    <div class="text-muted small">${safeLabel}</div>
    <div class="small">${renderedValue}</div>
  `;
}

function build_internal_fault_location_actions(location) {
  if (!location || !location.id) {
    return `
      <div class="text-muted small" style="margin-top: 10px;">
        No linked Location record is available.
      </div>
    `;
  }

  const buttons = [];

  if (location.route) {
    buttons.push(`
      <a class="btn btn-xs btn-default" href="${frappe.utils.escape_html(location.route)}">
        Open Location
      </a>
    `);
  }

  if (location.map_url) {
    buttons.push(`
      <a class="btn btn-xs btn-default"
         href="${frappe.utils.escape_html(location.map_url)}"
         target="_blank"
         rel="noopener noreferrer">
        View on map
      </a>
    `);
  }

  if (!buttons.length) {
    return `
      <div class="text-muted small" style="margin-top: 10px;">
        Map unavailable — no coordinates captured for this Location.
      </div>
    `;
  }

  return `
    <div style="margin-top: 12px; display: flex; gap: 8px; flex-wrap: wrap;">
      ${buttons.join("")}
    </div>
  `;
}

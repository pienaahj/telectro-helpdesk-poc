console.log("telectro_handoff_action.js loaded");

frappe.ui.form.on("HD Ticket", {
  refresh(frm) {
    setTimeout(() => {
      add_controlled_handoff_action(frm);
      add_share_ticket_context_action(frm);
    }, 300);
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

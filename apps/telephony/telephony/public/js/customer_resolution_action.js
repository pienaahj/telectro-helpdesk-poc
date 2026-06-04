frappe.ui.form.on("HD Ticket", {
  refresh(frm) {
    schedule_customer_actions(frm);
  },
  onload_post_render(frm) {
    schedule_customer_actions(frm);
  },
});

function schedule_customer_actions(frm) {
  add_customer_actions(frm);

  setTimeout(() => {
    add_customer_actions(frm);
  }, 300);

  setTimeout(() => {
    add_customer_actions(frm);
  }, 1000);
}

function add_customer_actions(frm) {
  add_customer_update_action(frm);
  add_customer_resolution_action(frm);
}

function add_customer_update_action(frm) {
  if (!should_show_customer_update_action(frm)) {
    return;
  }

  if (has_custom_button(frm, "Add Customer Update")) {
    return;
  }

  frm.add_custom_button(
    "Add Customer Update",
    () => {
      const dialog = new frappe.ui.Dialog({
        title: "Add Customer Update",
        fields: [
          {
            fieldname: "update_note",
            fieldtype: "Small Text",
            label: "Customer-visible update",
            reqd: 1,
            description:
              "This update will be visible to the Customer. Do not use internal notes here.",
          },
          {
            fieldname: "update_file",
            fieldtype: "Link",
            label: "Customer-visible update attachment",
            options: "File",
            reqd: 0,
            description:
              "Optional. Select a file already attached to this ticket if this Customer update needs a visible photo, sheet, or supporting document.",
            get_query() {
              return {
                filters: {
                  attached_to_doctype: "HD Ticket",
                  attached_to_name: frm.doc.name,
                },
              };
            },
          },
        ],
        primary_action_label: "Send update",
        primary_action(values) {
          const updateNote = (values.update_note || "").trim();

          if (!updateNote) {
            frappe.msgprint({
              title: __("Customer update required"),
              message: __("Please enter a Customer-visible update."),
              indicator: "orange",
            });
            return;
          }

          frappe.call({
            method: "telephony.customer_ticket_resolution.add_customer_update",
            args: {
              ticket_name: frm.doc.name,
              update_note: updateNote,
              update_file: values.update_file || "",
            },
            freeze: true,
            freeze_message: "Sending Customer update…",
            callback(r) {
              if (r.exc) {
                return;
              }

              dialog.hide();

              frappe.show_alert({
                message: __("Customer update sent"),
                indicator: "green",
              });

              frm.reload_doc();
            },
            error() {
              frappe.msgprint({
                title: __("Could not send Customer update"),
                message: __("Please check the ticket state and try again."),
                indicator: "red",
              });
            },
          });
        },
      });

      dialog.show();
    },
    "Customer",
  );
}

function add_customer_resolution_action(frm) {
  if (!should_show_customer_resolution_action(frm)) {
    return;
  }

  if (has_custom_button(frm, "Resolve Customer Ticket")) {
    return;
  }

  frm.add_custom_button(
    "Resolve Customer Ticket",
    () => {
      const dialog = new frappe.ui.Dialog({
        title: "Resolve Customer Ticket",
        fields: [
          {
            fieldname: "resolution_note",
            fieldtype: "Small Text",
            label: "Customer-visible resolution update",
            reqd: 1,
            description:
              "This update will be visible to the Customer. Do not use internal notes here.",
          },
          {
            fieldname: "completion_file",
            fieldtype: "Link",
            label: "Completion evidence file",
            options: "File",
            reqd: 0,
            description:
              "Optional. Select a file already attached to this ticket if the Customer needs a completion sheet, report, signed job card, or proof for their own records.",
            get_query() {
              return {
                filters: {
                  attached_to_doctype: "HD Ticket",
                  attached_to_name: frm.doc.name,
                },
              };
            },
          },
        ],
        primary_action_label: "Send update and resolve",
        primary_action(values) {
          const resolutionNote = (values.resolution_note || "").trim();

          if (!resolutionNote) {
            frappe.msgprint({
              title: __("Resolution update required"),
              message: __("Please enter a Customer-visible resolution update."),
              indicator: "orange",
            });
            return;
          }

          frappe.call({
            method:
              "telephony.customer_ticket_resolution.resolve_customer_ticket",
            args: {
              ticket_name: frm.doc.name,
              resolution_note: resolutionNote,
              completion_file: values.completion_file || "",
            },
            freeze: true,
            freeze_message: "Resolving Customer ticket…",
            callback(r) {
              if (r.exc) {
                return;
              }

              dialog.hide();

              frappe.show_alert({
                message: __("Customer ticket resolved"),
                indicator: "green",
              });

              frm.reload_doc();
            },
            error() {
              frappe.msgprint({
                title: __("Could not resolve Customer ticket"),
                message: __("Please check the ticket state and try again."),
                indicator: "red",
              });
            },
          });
        },
      });

      dialog.show();
    },
    "Customer",
  );
}

function should_show_customer_update_action(frm) {
  const d = frm.doc || {};

  if (!d.name || d.__islocal) {
    return false;
  }

  const status = (d.status || "").trim();
  if (["Closed", "Archived"].includes(status)) {
    return false;
  }

  if (!is_internal_telectro_user()) {
    return false;
  }

  return is_customer_ticket(d);
}

function should_show_customer_resolution_action(frm) {
  const d = frm.doc || {};

  if (!d.name || d.__islocal) {
    return false;
  }

  const status = (d.status || "").trim();
  if (["Resolved", "Closed"].includes(status)) {
    return false;
  }

  if (!is_internal_telectro_user()) {
    return false;
  }

  return is_customer_ticket(d);
}

function is_customer_ticket(d) {
  if (Boolean(d.via_customer_portal)) {
    return true;
  }

  if ((d.custom_request_source || "").trim() === "Customer") {
    return true;
  }

  if ((d.customer || "").trim() && (d.raised_by || "").trim()) {
    return true;
  }

  return false;
}

function is_internal_telectro_user() {
  const roles = frappe.user_roles || [];

  return [
    "System Manager",
    "TELECTRO-POC Role - Tech",
    "TELECTRO-POC Role - Coordinator Ops",
    "TELECTRO-POC Role - Supervisor Governance",
    "Agent",
  ].some((role) => roles.includes(role));
}

function has_custom_button(frm, label) {
  return Boolean(
    frm.custom_buttons &&
    frm.custom_buttons[label] &&
    frm.custom_buttons[label].length,
  );
}

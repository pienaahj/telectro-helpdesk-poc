console.log("partner_acceptance_review.js loaded");

frappe.ui.form.on("HD Ticket", {
  refresh(frm) {
    setTimeout(() => {
      add_request_partner_acceptance_action(frm);
      add_partner_acceptance_review_action(frm);
      add_partner_work_review_action(frm);
    }, 300);
  },
});

function add_request_partner_acceptance_action(frm) {
  if (!should_show_request_partner_acceptance(frm)) {
    return;
  }

  const state = (frm.doc.custom_partner_acceptance_state || "").trim();
  const buttonLabel =
    state === "Rework Required"
      ? "Request Partner Acceptance Again"
      : "Request Partner Acceptance";

  if (has_custom_button(frm, buttonLabel)) {
    return;
  }

  frm.add_custom_button(buttonLabel, () => {
    const dialog = new frappe.ui.Dialog({
      title: buttonLabel,
      fields: [
        {
          label: "Note",
          fieldname: "note",
          fieldtype: "Small Text",
          description: "Optional note for the Partner acceptance request",
        },
      ],
      primary_action_label: "Request",
      primary_action(values) {
        frappe.call({
          method: "telephony.partner_create.request_partner_acceptance",
          args: {
            ticket_name: frm.doc.name,
            note: values.note || "",
          },
          freeze: true,
          freeze_message: "Requesting Partner acceptance…",
          callback() {
            frappe.show_alert({
              message: __("Partner acceptance requested for {0}", [
                frm.doc.name,
              ]),
              indicator: "green",
            });

            dialog.hide();
            frm.reload_doc();
          },
          error(xhr) {
            console.error(xhr);
            frappe.msgprint({
              title: __("Request failed"),
              message: __("Could not request Partner acceptance."),
              indicator: "red",
            });
          },
        });
      },
    });

    dialog.show();
  });
}

function add_partner_acceptance_review_action(frm) {
  if (!should_show_partner_acceptance_review(frm)) {
    return;
  }

  if (has_custom_button(frm, "Review Partner Acceptance")) {
    return;
  }

  frm.add_custom_button("Review Partner Acceptance", () => {
    const dialog = new frappe.ui.Dialog({
      title: "Review Partner Acceptance",
      fields: [
        {
          label: "Outcome",
          fieldname: "outcome",
          fieldtype: "Select",
          options: ["Review only", "Resolve ticket", "Close ticket"].join("\n"),
          default: "Review only",
          reqd: 1,
        },
        {
          label: "Note",
          fieldname: "note",
          fieldtype: "Small Text",
          description: "Optional internal review note",
        },
      ],
      primary_action_label: "Apply",
      primary_action(values) {
        const outcomeMap = {
          "Review only": "review_only",
          "Resolve ticket": "resolve",
          "Close ticket": "close",
        };

        frappe.call({
          method: "telephony.partner_create.review_partner_acceptance",
          args: {
            ticket_name: frm.doc.name,
            outcome: outcomeMap[values.outcome],
            note: values.note || "",
          },
          freeze: true,
          freeze_message: "Applying Partner acceptance review…",
          callback() {
            frappe.show_alert({
              message: __("Partner acceptance reviewed for {0}", [
                frm.doc.name,
              ]),
              indicator: "green",
            });

            dialog.hide();
            frm.reload_doc();
          },
          error(xhr) {
            console.error(xhr);
            frappe.msgprint({
              title: __("Review failed"),
              message: __("Could not apply the Partner acceptance review."),
              indicator: "red",
            });
          },
        });
      },
    });

    dialog.show();
  });
}

function should_show_request_partner_acceptance(frm) {
  const d = frm.doc || {};

  if (!d.name || frm.is_new()) {
    return false;
  }

  if (d.doctype !== "HD Ticket") {
    return false;
  }

  if ((d.custom_request_source || "") !== "Partner") {
    return false;
  }

  if ((d.custom_fulfilment_party || "").trim() === "Partner") {
    return false;
  }

  const state = (d.custom_partner_acceptance_state || "").trim();
  if (!["", "Rework Required"].includes(state)) {
    return false;
  }

  const partnerWorkState = (d.custom_partner_work_state || "").trim();
  if (partnerWorkState !== "") {
    return false;
  }

  if (["Resolved", "Closed", "Archived"].includes(d.status || "")) {
    return false;
  }

  return has_internal_acceptance_review_role();
}

function has_internal_acceptance_review_role() {
  return [
    "System Manager",
    "Pilot Admin",
    "TELECTRO-POC Ops Role",
    "TELECTRO-POC Coordinator Role",
    "TELECTRO-POC Role - Supervisor Governance",
    "TELECTRO-POC Role - Coordinator Ops",
  ].some((role) => frappe.user.has_role(role));
}

function has_custom_button(frm, label) {
  return !!frm.custom_buttons?.[label];
}

function add_partner_work_review_action(frm) {
  if (!should_show_partner_work_review(frm)) {
    return;
  }

  if (has_custom_button(frm, "Review Partner Work")) {
    return;
  }

  frm.add_custom_button("Review Partner Work", () => {
    const workState = (frm.doc.custom_partner_work_state || "").trim();

    const outcomeOptions =
      workState === "Reviewed by Telectro"
        ? ["Resolve ticket", "Close ticket"]
        : [
            "Review only",
            "Accept work",
            "Request Rework",
            "Resolve ticket",
            "Close ticket",
          ];

    const dialog = new frappe.ui.Dialog({
      title: "Review Partner Work",
      fields: [
        {
          label: "Outcome",
          fieldname: "outcome",
          fieldtype: "Select",
          options: outcomeOptions.join("\n"),
          default: outcomeOptions[0],
          reqd: 1,
        },
        {
          label: "Note",
          fieldname: "note",
          fieldtype: "Small Text",
          description:
            "Required when requesting rework. Optional for other outcomes.",
        },
      ],
      primary_action_label: "Apply",
      primary_action(values) {
        const outcomeMap = {
          "Review only": "review_only",
          "Accept work": "accept",
          "Request Rework": "rework_required",
          "Resolve ticket": "resolve",
          "Close ticket": "close",
        };

        if (
          values.outcome === "Request Rework" &&
          (!values.note || !values.note.trim())
        ) {
          frappe.msgprint("Please enter a rework reason.");
          return;
        }

        frappe.call({
          method: "telephony.partner_create.review_partner_work_completion",
          args: {
            ticket_name: frm.doc.name,
            outcome: outcomeMap[values.outcome],
            note: values.note || "",
          },
          freeze: true,
          freeze_message: "Applying Partner work review...",
          callback() {
            frappe.show_alert({
              message: __("Partner work reviewed for {0}", [frm.doc.name]),
              indicator: "green",
            });

            dialog.hide();
            frm.reload_doc();
          },
          error(xhr) {
            console.error(xhr);
            frappe.msgprint({
              title: __("Review failed"),
              message: __("Could not apply Partner work review."),
              indicator: "red",
            });
          },
        });
      },
    });

    dialog.show();
  });
}

function should_show_partner_acceptance_review(frm) {
  const d = frm.doc || {};

  if (!d.name || frm.is_new()) {
    return false;
  }

  if (d.doctype !== "HD Ticket") {
    return false;
  }

  if ((d.custom_request_source || "").trim() !== "Partner") {
    return false;
  }

  if ((d.custom_fulfilment_party || "").trim() === "Partner") {
    return false;
  }

  if (
    (d.custom_partner_acceptance_state || "").trim() !== "Accepted by Partner"
  ) {
    return false;
  }

  if (["Resolved", "Closed", "Archived"].includes(d.status || "")) {
    return false;
  }

  return has_internal_acceptance_review_role();
}

function should_show_partner_work_review(frm) {
  const d = frm.doc || {};

  if (!d.name || frm.is_new()) {
    return false;
  }

  if (d.doctype !== "HD Ticket") {
    return false;
  }

  if ((d.custom_fulfilment_party || "").trim() !== "Partner") {
    return false;
  }

  if ((d.custom_request_source || "").trim() === "Partner") {
    return false;
  }

  const workState = (d.custom_partner_work_state || "").trim();

  if (
    !["Work Completed by Partner", "Reviewed by Telectro"].includes(workState)
  ) {
    return false;
  }

  if (["Resolved", "Closed", "Archived"].includes(d.status || "")) {
    return false;
  }

  return has_internal_acceptance_review_role();
}

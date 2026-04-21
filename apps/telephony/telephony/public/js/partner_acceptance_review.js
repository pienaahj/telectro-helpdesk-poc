console.log("partner_acceptance_review.js loaded");

// frappe.ui.form.on("HD Ticket", {
//   refresh(frm) {
//     add_partner_acceptance_review_action(frm);
//   },
// });

frappe.ui.form.on("HD Ticket", {
  refresh(frm) {
    if (frappe.user.has_role("Pilot Admin")) {
      frm.add_custom_button("DEBUG Partner Acceptance", () => {
        frappe.msgprint(
          `<pre>${frappe.utils.escape_html(
            JSON.stringify(
              {
                name: frm.doc?.name,
                request_source: frm.doc?.custom_request_source,
                acceptance_state: frm.doc?.custom_partner_acceptance_state,
                status: frm.doc?.status,
                roles: frappe.user_roles,
              },
              null,
              2,
            ),
          )}</pre>`,
        );
      });
    }

    setTimeout(() => {
      add_partner_acceptance_review_action(frm);
    }, 300);
  },
});

function add_partner_acceptance_review_action(frm) {
  if (!should_show_partner_acceptance_review(frm)) {
    return;
  }

  frm.add_custom_button(
    "Review Partner Acceptance",
    () => {
      const dialog = new frappe.ui.Dialog({
        title: "Review Partner Acceptance",
        fields: [
          {
            label: "Outcome",
            fieldname: "outcome",
            fieldtype: "Select",
            options: ["Review only", "Resolve ticket", "Close ticket"].join(
              "\n",
            ),
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
            callback(r) {
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
    },
    // "Actions",
  );
}

function should_show_partner_acceptance_review(frm) {
  const d = frm.doc || {};

  if (!d.name || frm.is_new()) {
    console.log("hide: new or missing name");
    return false;
  }

  if (d.doctype !== "HD Ticket") {
    console.log("hide: not HD Ticket");
    return false;
  }

  if ((d.custom_request_source || "") !== "Partner") {
    console.log("hide: request source mismatch");
    return false;
  }

  if ((d.custom_partner_acceptance_state || "") !== "Accepted by Partner") {
    console.log("hide: acceptance state mismatch");
    return false;
  }

  if (["Resolved", "Closed", "Archived"].includes(d.status || "")) {
    console.log("hide: terminal status");
    return false;
  }

  const allowed = has_internal_acceptance_review_role();
  console.log("role check result", allowed);
  return allowed;
}

function has_internal_acceptance_review_role() {
  const roles = frappe.user_roles || [];
  const allowed = new Set([
    "System Manager",
    "Pilot Admin",
    "TELECTRO-POC Ops Role",
    "TELECTRO-POC Coordinator Role",
    "TELECTRO-POC Role - Supervisor Governance",
    "TELECTRO-POC Role - Coordinator Ops",
  ]);

  return roles.some((role) => allowed.has(role));
}

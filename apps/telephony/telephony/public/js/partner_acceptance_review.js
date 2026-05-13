console.log("partner_acceptance_review.js loaded");

frappe.ui.form.on("HD Ticket", {
  refresh(frm) {
    setTimeout(() => {
      add_request_partner_acceptance_action(frm);
      add_partner_acceptance_review_action(frm);
      add_partner_work_review_action(frm);
      add_ticket_evidence_action(frm);
    }, 300);
  },
});

function getInternalAttachmentDownloadUrl(ticketName, fileId) {
  return (
    "/api/method/telephony.partner_create.download_internal_ticket_attachment" +
    `?ticket_name=${encodeURIComponent(ticketName)}` +
    `&file_id=${encodeURIComponent(fileId)}`
  );
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onload = () => resolve(reader.result);
    reader.onerror = () =>
      reject(reader.error || new Error("Could not read file"));

    reader.readAsDataURL(file);
  });
}

function renderTicketEvidenceRows(ticketName, files) {
  const rows = files.length
    ? files
        .map((file) => {
          const url = getInternalAttachmentDownloadUrl(ticketName, file.name);
          const fileName = frappe.utils.escape_html(
            file.file_name || file.name || "Attachment",
          );
          const owner = frappe.utils.escape_html(file.owner || "");
          const creation = frappe.utils.escape_html(file.creation || "");

          return `
            <a class="list-group-item list-group-item-action"
               href="${url}"
               target="_blank"
               rel="noopener">
              <div class="font-weight-bold">${fileName}</div>
              <div class="text-muted small">
                ${[owner, creation].filter(Boolean).join(" • ")}
              </div>
            </a>
          `;
        })
        .join("")
    : `<div class="text-muted">No ticket evidence has been uploaded yet.</div>`;

  return `
    <div class="mb-3 text-muted">
      Photos, WhatsApp images, quotes, and supporting documents attached to this ticket.
    </div>
    <div class="list-group">
      ${rows}
    </div>
  `;
}

function refreshTicketEvidenceDialog(frm, dialog) {
  frappe.call({
    method: "telephony.partner_create.get_internal_ticket_attachments",
    args: {
      ticket_name: frm.doc.name,
    },
    freeze: true,
    freeze_message: "Refreshing ticket evidence…",
    callback(r) {
      const files = r.message || [];
      dialog.fields_dict.evidence_html.$wrapper.html(
        renderTicketEvidenceRows(frm.doc.name, files),
      );
    },
    error(xhr) {
      console.error(xhr);
      frappe.msgprint({
        title: __("Could not refresh ticket evidence"),
        message: __("The ticket evidence list could not be refreshed."),
        indicator: "red",
      });
    },
  });
}

function should_show_ticket_evidence_action(frm) {
  const d = frm.doc || {};

  if (!d.name || frm.is_new()) {
    return false;
  }

  if (d.doctype !== "HD Ticket") {
    return false;
  }

  return (
    has_internal_acceptance_review_role() ||
    frappe.user.has_role("TELECTRO-POC Role - Tech")
  );
}

function add_ticket_evidence_action(frm) {
  if (!should_show_ticket_evidence_action(frm)) {
    return;
  }

  if (has_custom_button(frm, "Ticket Evidence")) {
    return;
  }

  frm.add_custom_button("Ticket Evidence", () => {
    frappe.call({
      method: "telephony.partner_create.get_internal_ticket_attachments",
      args: {
        ticket_name: frm.doc.name,
      },
      freeze: true,
      freeze_message: "Loading ticket evidence…",
      callback(r) {
        show_ticket_evidence_dialog(frm, r.message || []);
      },
      error(xhr) {
        console.error(xhr);
        frappe.msgprint({
          title: __("Could not load ticket evidence"),
          message: __("The ticket evidence list could not be loaded."),
          indicator: "red",
        });
      },
    });
  });
}

function makeEvidencePhotoFilename() {
  const stamp = frappe.datetime
    .now_datetime()
    .replace(/[-: ]/g, "")
    .replace(/\..*$/, "");

  return `ticket-evidence-photo-${stamp}.png`;
}

function uploadInternalEvidenceDataUrl(frm, fileName, filedata, contentType) {
  return frappe.call({
    method: "telephony.partner_create.upload_internal_ticket_attachment",
    args: {
      ticket_name: frm.doc.name,
      file_name: fileName,
      filedata,
      content_type: contentType || "image/png",
    },
    freeze: true,
    freeze_message: "Uploading captured photo…",
  });
}

async function showCapturePhotoDialog(frm, parentDialog) {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    frappe.msgprint({
      title: __("Camera not available"),
      message: __(
        "This browser does not support direct camera capture. Please upload a JPG or PNG file instead.",
      ),
      indicator: "orange",
    });
    return;
  }

  let stream = null;

  const dialog = new frappe.ui.Dialog({
    title: "Capture Evidence Photo",
    size: "large",
    fields: [
      {
        fieldname: "camera_html",
        fieldtype: "HTML",
        options: `
          <div class="ticket-evidence-camera">
            <video
              class="ticket-evidence-video"
              autoplay
              playsinline
              style="width:100%; max-height:60vh; background:#111; border-radius:8px;"
            ></video>
            <canvas class="ticket-evidence-canvas" style="display:none;"></canvas>
            <div class="text-muted small mt-2">
              Captured photos are stored as PNG ticket evidence.
            </div>
          </div>
        `,
      },
    ],
    primary_action_label: "Capture and Upload",
    async primary_action() {
      const video = dialog.$wrapper.find(".ticket-evidence-video").get(0);
      const canvas = dialog.$wrapper.find(".ticket-evidence-canvas").get(0);

      if (!video || !canvas || !video.videoWidth || !video.videoHeight) {
        frappe.msgprint("Camera is not ready yet. Please try again.");
        return;
      }

      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;

      const ctx = canvas.getContext("2d");
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

      const filedata = canvas.toDataURL("image/png");
      const fileName = makeEvidencePhotoFilename();

      try {
        await uploadInternalEvidenceDataUrl(
          frm,
          fileName,
          filedata,
          "image/png",
        );

        frappe.show_alert({
          message: __("Captured photo uploaded."),
          indicator: "green",
        });

        dialog.hide();
        refreshTicketEvidenceDialog(frm, parentDialog);
      } catch (e) {
        console.error(e);
        frappe.msgprint({
          title: __("Photo upload failed"),
          message: e?.message || __("Could not upload captured photo."),
          indicator: "red",
        });
      }
    },
  });

  dialog.onhide = () => {
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
    }
  };

  dialog.show();

  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: { ideal: "environment" },
      },
      audio: false,
    });

    const video = dialog.$wrapper.find(".ticket-evidence-video").get(0);
    video.srcObject = stream;
  } catch (e) {
    console.error(e);

    frappe.msgprint({
      title: __("Camera access failed"),
      message: __(
        "Could not access the camera. Check browser permissions, or upload a JPG/PNG file instead.",
      ),
      indicator: "red",
    });

    dialog.hide();
  }
}

function show_ticket_evidence_dialog(frm, files) {
  const dialog = new frappe.ui.Dialog({
    title: "Ticket Evidence",
    size: "large",
    fields: [
      {
        fieldname: "evidence_html",
        fieldtype: "HTML",
        options: renderTicketEvidenceRows(frm.doc.name, files),
      },
      {
        fieldname: "upload_section",
        fieldtype: "Section Break",
        label: "Add Evidence",
      },
      {
        fieldname: "upload_html",
        fieldtype: "HTML",
        options: `
          <style>
            .ticket-evidence-upload-row {
              display: grid;
              grid-template-columns: minmax(0, 1fr) auto;
              gap: 0.75rem;
              align-items: center;
            }

            .ticket-evidence-upload-row .internal-evidence-capture-photo {
              white-space: nowrap;
              min-width: 120px;
            }

            @media (max-width: 576px) {
              .ticket-evidence-upload-row {
                grid-template-columns: 1fr;
              }

              .ticket-evidence-upload-row .internal-evidence-capture-photo {
                width: 100%;
              }
            }
          </style>

          <div class="ticket-evidence-upload mt-2">
            <label class="control-label">Add Evidence</label>

            <div class="ticket-evidence-upload-row">
              <input
                type="file"
                class="form-control internal-evidence-file-input"
                accept=".jpg,.jpeg,.png,.pdf,.doc,.docx,.xls,.xlsx,.txt"
              />

              <button
                type="button"
                class="btn btn-default internal-evidence-capture-photo"
              >
                Take Photo
              </button>
            </div>

            <div class="text-muted small mt-2">
              Maximum size: 10 MB. JPG, PNG, PDF, Word, Excel, and text files are supported in V1.
              Files are stored privately and attached to this HD Ticket.
            </div>
          </div>
        `,
      },
    ],
    primary_action_label: "Upload Selected File",
    primary_action() {
      const input = dialog.$wrapper.find(".internal-evidence-file-input")[0];
      const file = input && input.files && input.files[0];

      if (!file) {
        frappe.msgprint("Please choose a file to upload.");
        return;
      }

      const maxBytes = 10 * 1024 * 1024;
      if (file.size > maxBytes) {
        frappe.msgprint("File is too large. Maximum size is 10 MB.");
        return;
      }

      readFileAsDataUrl(file)
        .then((filedata) =>
          frappe.call({
            method:
              "telephony.partner_create.upload_internal_ticket_attachment",
            args: {
              ticket_name: frm.doc.name,
              file_name: file.name,
              filedata,
              content_type: file.type || null,
            },
            freeze: true,
            freeze_message: "Uploading ticket evidence…",
          }),
        )
        .then(() => {
          frappe.show_alert({
            message: __("Evidence uploaded."),
            indicator: "green",
          });

          input.value = "";
          refreshTicketEvidenceDialog(frm, dialog);
        })
        .catch((error) => {
          console.error(error);
          frappe.msgprint({
            title: __("Evidence upload failed"),
            message: error.message || __("Could not upload ticket evidence."),
            indicator: "red",
          });
        });
    },
  });

  dialog.show();
  dialog.$wrapper.find(".internal-evidence-capture-photo").on("click", () => {
    showCapturePhotoDialog(frm, dialog);
  });
}

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

frappe.pages["partner-ticket"].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: "Partner Ticket",
    single_column: true,
  });

  const $body = $(wrapper).find(".layout-main-section");
  $body.empty();

  $body.append(`
    <div class="partner-ticket-page">
      <div class="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h3 class="mb-1" id="pt-title">Partner Ticket</h3>
          <div class="text-muted small" id="pt-meta"></div>
        </div>
        <div class="d-flex gap-2">
          <button class="btn btn-default btn-sm" id="pt-back-submitted">Tickets Submitted by Partner</button>
          <button class="btn btn-default btn-sm" id="pt-back-active">Tickets Assigned to Partner</button>
          <button class="btn btn-default btn-sm" id="pt-back-archived">Partner History</button>
          <button class="btn btn-default btn-sm" id="pt-request-rework" style="display:none;">
            Request Rework
          </button>
          <button class="btn btn-primary btn-sm" id="pt-submit-completion" style="display:none;">
            Submit Acceptance Note
          </button>
        </div>
      </div>

      <div class="alert alert-primary mb-4">
        This is a Partner-safe ticket view.
      </div>

      <div id="pt-error" class="alert alert-danger" style="display:none;"></div>

      <div id="pt-content" style="display:none;">
        <div class="row mb-4">
          <div class="col-md-6">
            <table class="table table-bordered">
              <tbody>
                <tr><th style="width:35%;">ID</th><td id="pt-name"></td></tr>
                <tr><th>Status</th><td id="pt-status"></td></tr>
                <tr><th>Priority</th><td id="pt-priority"></td></tr>
                <tr><th>Request Type</th><td id="pt-request-type"></td></tr>
                <tr><th>Due Date</th><td id="pt-due-date"></td></tr>
                <tr><th>Ticket Type</th><td id="pt-ticket-type"></td></tr>
                <tr><th>Request Source</th><td id="pt-request-source"></td></tr>
                <tr><th>Fulfilment Party</th><td id="pt-fulfilment-party"></td></tr>
              </tbody>
            </table>
          </div>

          <div class="col-md-6">
            <table class="table table-bordered">
              <tbody>
                <tr><th style="width:35%;">Customer</th><td id="pt-customer"></td></tr>
                <tr><th>Campus</th><td id="pt-site-group"></td></tr>
                <tr><th>Fault Category</th><td id="pt-fault-category"></td></tr>
                <tr><th>Fault Asset</th><td id="pt-fault-asset"></td></tr>
                <tr><th>Fault Point</th><td id="pt-site"></td></tr>
                <tr><th>Ownership</th><td id="pt-ownership-model"></td></tr>
                <tr><th>Service Area</th><td id="pt-service-area"></td></tr>
                <tr><th>Severity</th><td id="pt-severity"></td></tr>
                <tr><th>Partner Work State</th><td id="pt-partner-work-state"></td></tr>
                <tr><th>Partner Work Completed</th><td id="pt-partner-work-completed"></td></tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="card">
          <div class="card-body">
            <h5 class="mb-3">Subject</h5>
            <div id="pt-subject" class="mb-4 font-weight-bold"></div>

            <h5 class="mb-3">Summary</h5>
            <div id="pt-summary" class="mb-4" style="white-space: pre-wrap;"></div>

            <hr>

            <div id="pt-attachments-section">
              <div class="d-flex justify-content-between align-items-center mb-2">
                <h5 class="mb-0">Attachments</h5>
                <button class="btn btn-default btn-sm" id="pt-upload-attachment">
                  Upload Attachment
                </button>
              </div>

              <div class="text-muted small mb-2">
                Upload supporting evidence, photos, quotes, or documents for this ticket.
              </div>

              <div id="pt-attachments-empty" class="text-muted small">
                No attachments found.
              </div>

              <div id="pt-attachments-list" class="list-group"></div>
            </div>

            <div id="pt-partner-notes" style="display:none;">
              <hr>

              <div id="pt-partner-acceptance-note-section" style="display:none;">
                <h5 class="mb-3">Partner Acceptance Note</h5>
                <div id="pt-partner-acceptance-note" class="mb-4" style="white-space: pre-wrap;"></div>
              </div>

              <div id="pt-partner-rework-note-section" style="display:none;">
                <h5 class="mb-3">Rework Required</h5>
                <div id="pt-partner-rework-note" style="white-space: pre-wrap;"></div>
              </div>

              <div id="pt-partner-work-done-note-section" style="display:none;">
                <h5 class="mb-3">Partner Work Done Note</h5>
                <div id="pt-partner-work-done-note" class="mb-4" style="white-space: pre-wrap;"></div>
              </div>

              <div id="pt-partner-work-rework-note-section" style="display:none;">
                <h5 class="mb-3">Partner Work Rework Required</h5>
                <div id="pt-partner-work-rework-note" class="mb-4" style="white-space: pre-wrap;"></div>
              </div>

              <div id="pt-partner-work-review-note-section" style="display:none;">
                <h5 class="mb-3">Partner Work Review</h5>
                <div id="pt-partner-work-review-note" class="mb-4" style="white-space: pre-wrap;"></div>
              </div>

              <div id="pt-partner-work-review-note-section" style="display:none;">
                <h5 class="mb-3">Partner Work Review</h5>
                <div id="pt-partner-work-review-note" class="mb-4" style="white-space: pre-wrap;"></div>
              </div>

              <div id="pt-partner-review-note-section" style="display:none;">
                <h5 class="mb-3">Telectro Review Note</h5>
                <div id="pt-partner-review-note" style="white-space: pre-wrap;"></div>
              </div>

              <div id="pt-partner-acceptance-request-note-section" style="display:none;">
                <h5 class="mb-3">Partner Acceptance Requested</h5>
                <div id="pt-partner-acceptance-request-note" class="mb-4" style="white-space: pre-wrap;"></div>
              </div>

              <div id="pt-partner-acceptance-request-note-section" style="display:none;">
                <h5 class="mb-3">Partner Acceptance Requested</h5>
                <div id="pt-partner-acceptance-request-note" class="mb-4" style="white-space: pre-wrap;"></div>
              </div>

            </div>
          </div>
        </div>
      </div>
    </div>
  `);

  function makeEvidencePhotoFilename() {
    const stamp = frappe.datetime
      .now_datetime()
      .replace(/[-: ]/g, "")
      .replace(/\..*$/, "");

    return `partner-ticket-evidence-photo-${stamp}.png`;
  }

  function uploadPartnerEvidenceDataUrl(
    ticketName,
    fileName,
    filedata,
    contentType,
  ) {
    return frappe.call({
      method: "telephony.partner_create.upload_partner_ticket_attachment",
      args: {
        ticket_name: ticketName,
        file_name: fileName,
        filedata,
        content_type: contentType || "image/png",
      },
      freeze: true,
      freeze_message: "Uploading captured photo…",
    });
  }

  async function showCapturePhotoDialog(ticketName) {
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
      title: "Take Evidence Photo",
      size: "large",
      fields: [
        {
          fieldname: "camera_html",
          fieldtype: "HTML",
          options: `
            <div class="partner-ticket-evidence-camera">
              <video
                class="partner-ticket-evidence-video"
                autoplay
                playsinline
                style="width:100%; max-height:60vh; background:#111; border-radius:8px;"
              ></video>
              <canvas class="partner-ticket-evidence-canvas" style="display:none;"></canvas>
              <div class="text-muted small mt-2">
                Captured photos are stored as PNG ticket evidence.
              </div>
            </div>
          `,
        },
      ],
      primary_action_label: "Capture and Upload",
      async primary_action() {
        const video = dialog.$wrapper
          .find(".partner-ticket-evidence-video")
          .get(0);
        const canvas = dialog.$wrapper
          .find(".partner-ticket-evidence-canvas")
          .get(0);

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
          await uploadPartnerEvidenceDataUrl(
            ticketName,
            fileName,
            filedata,
            "image/png",
          );

          frappe.show_alert({
            message: __("Captured photo uploaded."),
            indicator: "green",
          });

          dialog.hide();
          loadAttachments(ticketName);
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

      const video = dialog.$wrapper
        .find(".partner-ticket-evidence-video")
        .get(0);
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

  function readFileAsDataUrl(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();

      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(reader.error);

      reader.readAsDataURL(file);
    });
  }

  function getTicketName() {
    const route = frappe.get_route() || [];
    return route[1];
  }

  function setText(id, value) {
    $body.find(id).text(value || "");
  }

  function htmlToText(value) {
    if (!value) {
      return "";
    }

    const wrapper = document.createElement("div");
    wrapper.innerHTML = value;

    return (wrapper.innerText || wrapper.textContent || "").trim();
  }

  function getAttachmentDownloadUrl(ticketName, fileId) {
    return (
      "/api/method/telephony.partner_create.download_partner_ticket_attachment" +
      `?ticket_name=${encodeURIComponent(ticketName)}` +
      `&file_id=${encodeURIComponent(fileId)}`
    );
  }

  function renderAttachments(ticketName, attachments) {
    const $empty = $body.find("#pt-attachments-empty");
    const $list = $body.find("#pt-attachments-list");

    $list.empty();

    if (!attachments || !attachments.length) {
      $empty.show();
      return;
    }

    $empty.hide();

    attachments.forEach((file) => {
      const fileName = file.file_name || file.name || "Attachment";
      const owner = file.owner || "";
      const created = file.creation || "";
      const url = getAttachmentDownloadUrl(ticketName, file.name);

      const $item = $(`
        <a
          class="list-group-item list-group-item-action d-flex justify-content-between align-items-center"
          href="${url}"
          target="_blank"
          rel="noopener"
        >
          <div>
            <div class="font-weight-bold"></div>
            <div class="text-muted small"></div>
          </div>
          <span class="text-muted small">Download</span>
        </a>
      `);

      $item.find(".font-weight-bold").text(fileName);
      $item
        .find(".text-muted.small")
        .text([owner, created].filter(Boolean).join(" • "));

      $list.append($item);
    });
  }

  function loadAttachments(ticketName) {
    $body.find("#pt-attachments-empty").text("Loading attachments…").show();
    $body.find("#pt-attachments-list").empty();

    frappe.call({
      method: "telephony.partner_create.get_partner_ticket_attachments",
      args: { ticket_name: ticketName },
      callback(r) {
        $body.find("#pt-attachments-empty").text("No attachments found.");
        renderAttachments(ticketName, r.message || []);
      },
      error(xhr) {
        console.error(xhr);
        $body
          .find("#pt-attachments-empty")
          .text("Could not load attachments.")
          .show();
        $body.find("#pt-attachments-list").empty();
      },
    });
  }

  async function uploadSelectedAttachment(ticketName, file) {
    if (!file) {
      frappe.msgprint("Please choose a file to upload.");
      return;
    }

    const maxBytes = 10 * 1024 * 1024;
    if (file.size > maxBytes) {
      frappe.msgprint("File is too large. Maximum size is 10 MB.");
      return;
    }

    const filedata = await readFileAsDataUrl(file);

    await frappe.call({
      method: "telephony.partner_create.upload_partner_ticket_attachment",
      args: {
        ticket_name: ticketName,
        file_name: file.name,
        filedata,
        content_type: file.type || "",
      },
      freeze: true,
      freeze_message: "Uploading attachment…",
    });

    frappe.show_alert({
      message: __("Attachment uploaded for {0}", [ticketName]),
      indicator: "green",
    });

    loadAttachments(ticketName);
  }

  function showUploadAttachmentDialog(ticketName) {
    const dialog = new frappe.ui.Dialog({
      title: "Upload Attachment",
      fields: [
        {
          fieldname: "upload_html",
          fieldtype: "HTML",
          options: `
            <style>
              .partner-ticket-upload-row {
                display: grid;
                grid-template-columns: minmax(0, 1fr) auto;
                gap: 0.75rem;
                align-items: center;
              }

              .partner-ticket-upload-row .partner-ticket-capture-photo {
                white-space: nowrap;
                min-width: 120px;
              }

              @media (max-width: 576px) {
                .partner-ticket-upload-row {
                  grid-template-columns: 1fr;
                }

                .partner-ticket-upload-row .partner-ticket-capture-photo {
                  width: 100%;
                }
              }
            </style>

            <div class="form-group">
              <label class="control-label">Add Evidence</label>

              <div class="partner-ticket-upload-row">
                <input
                  type="file"
                  class="form-control"
                  id="pt-upload-file-input"
                  accept=".jpg,.jpeg,.png,.pdf,.doc,.docx,.xls,.xlsx,.txt"
                >

                <button
                  type="button"
                  class="btn btn-default partner-ticket-capture-photo"
                >
                  Take Photo
                </button>
              </div>

              <p class="text-muted small mt-2">
                Maximum size: 10 MB. JPG, PNG, PDF, Word, Excel, and text files are supported in V1.
                Files are stored privately and attached to this ticket.
              </p>
            </div>
          `,
        },
      ],
      primary_action_label: "Upload Selected File",
      async primary_action() {
        const file = dialog.$wrapper.find("#pt-upload-file-input").get(0)
          ?.files?.[0];

        if (!file) {
          frappe.msgprint("Please choose a file to upload.");
          return;
        }

        try {
          await uploadSelectedAttachment(ticketName, file);
          dialog.hide();
        } catch (e) {
          console.error(e);
          frappe.msgprint({
            title: __("Upload failed"),
            message: __("Could not upload the attachment."),
            indicator: "red",
          });
        }
      },
    });

    dialog.show();
    dialog.$wrapper.find(".partner-ticket-capture-photo").on("click", () => {
      showCapturePhotoDialog(ticketName);
    });
  }

  function clearText() {
    [
      "#pt-title",
      "#pt-meta",
      "#pt-name",
      "#pt-status",
      "#pt-priority",
      "#pt-request-type",
      "#pt-due-date",
      "#pt-ticket-type",
      "#pt-request-source",
      "#pt-fulfilment-party",
      "#pt-customer",
      "#pt-site-group",
      "#pt-fault-category",
      "#pt-fault-asset",
      "#pt-site",
      "#pt-ownership-model",
      "#pt-service-area",
      "#pt-severity",
      "#pt-subject",
      "#pt-summary",
      "#pt-partner-work-state",
      "#pt-partner-work-completed",
      "#pt-partner-acceptance-note",
      "#pt-partner-work-done-note",
      "#pt-partner-review-note",
      "#pt-partner-rework-note",
      "#pt-partner-work-rework-note",
      "#pt-partner-work-review-note",
      "#pt-partner-acceptance-request-note",
      "#pt-partner-acceptance-request-note",
    ].forEach((id) => setText(id, ""));

    $body.find("#pt-partner-notes").hide();
    $body.find("#pt-partner-acceptance-note-section").hide();
    $body.find("#pt-partner-work-done-note-section").hide();
    $body.find("#pt-partner-review-note-section").hide();
    $body.find("#pt-partner-work-rework-note-section").hide();
    $body.find("#pt-partner-work-review-note-section").hide();
    $body.find("#pt-partner-acceptance-request-note-section").hide();
    $body.find("#pt-partner-acceptance-request-note-section").hide();
    $body.find("#pt-request-rework").hide();
    $body.find("#pt-request-rework").removeData("action");
  }

  function getPartnerTicketTrain(d) {
    const requestSource = (d?.custom_request_source || "").trim();
    const fulfilmentParty = (d?.custom_fulfilment_party || "").trim();

    const isPartnerToTelectro =
      requestSource === "Partner" && fulfilmentParty !== "Partner";

    const isTelectroToPartner =
      requestSource !== "Partner" && fulfilmentParty === "Partner";

    return {
      isPartnerToTelectro,
      isTelectroToPartner,
    };
  }

  function hasPartnerAccepted(d) {
    const state = (d?.custom_partner_acceptance_state || "").trim();
    return state === "Accepted by Partner" || state === "Reviewed by Telectro";
  }

  function updatePartnerAction(d) {
    const $reworkBtn = $body.find("#pt-request-rework");
    const $btn = $body.find("#pt-submit-completion");
    const train = getPartnerTicketTrain(d);
    const status = (d?.status || "").trim();
    const acceptanceState = (d?.custom_partner_acceptance_state || "").trim();
    const workState = (d?.custom_partner_work_state || "").trim();

    $btn.hide();
    $btn.removeData("action");
    $reworkBtn.hide();
    $reworkBtn.removeData("action");

    if (["Resolved", "Closed", "Archived"].includes(status)) {
      return;
    }

    if (train.isPartnerToTelectro) {
      if (acceptanceState === "Pending Partner Acceptance") {
        $btn.text("Submit Acceptance Note");
        $btn.data("action", "acceptance-note");
        $btn.show();

        $reworkBtn.text("Request Rework");
        $reworkBtn.data("action", "acceptance-rework");
        $reworkBtn.show();
      }

      return;
    }

    if (train.isTelectroToPartner) {
      if (
        workState === "" ||
        workState === "Assigned to Partner" ||
        workState === "Rework Required"
      ) {
        $btn.text("Submit Work Done");
        $btn.data("action", "work-done");
        $btn.show();
      }
      return;
    }
  }

  function showError(message) {
    $body.find("#pt-submit-completion").hide();
    $body.find("#pt-request-rework").hide();
    $body
      .find("#pt-error")
      .text(message || "Could not load ticket.")
      .show();
    $body.find("#pt-content").hide();
  }

  function showContent() {
    $body.find("#pt-error").hide();
    $body.find("#pt-content").show();
  }

  function loadTicket() {
    const ticketName = getTicketName();

    if (!ticketName) {
      showError("Missing ticket name.");
      return;
    }

    clearText();
    $body.find("#pt-error").hide();
    $body.find("#pt-content").hide();
    $body.find("#pt-submit-completion").hide();
    $body.find("#pt-request-rework").hide();

    page.set_title(`Partner Ticket ${ticketName}`);
    page.set_indicator("Loading…", "blue");

    frappe.call({
      method: "telephony.partner_create.get_partner_ticket_detail",
      args: { ticket_name: ticketName },
      callback: function (r) {
        const d = r.message;
        if (!d) {
          showError("Ticket not found.");
          page.set_indicator("");
          return;
        }

        setText("#pt-title", `Partner Ticket ${d.name || ticketName}`);
        setText(
          "#pt-meta",
          [d.status, d.priority, d.modified].filter(Boolean).join(" • "),
        );

        setText("#pt-name", d.name);
        setText("#pt-status", d.status);
        setText("#pt-priority", d.priority);
        setText("#pt-request-type", d.custom_request_type);
        setText("#pt-due-date", d.custom_due_date);
        setText("#pt-ticket-type", d.ticket_type);
        setText("#pt-request-source", d.custom_request_source);
        setText("#pt-fulfilment-party", d.custom_fulfilment_party);

        setText("#pt-customer", d.custom_customer);
        setText("#pt-site-group", d.custom_site_group);
        setText("#pt-fault-category", d.custom_fault_category);
        setText("#pt-fault-asset", d.custom_fault_asset);
        setText("#pt-site", d.custom_site);
        setText("#pt-ownership-model", d.custom_ownership_model);
        setText("#pt-service-area", d.custom_service_area);
        setText("#pt-severity", d.custom_severity);
        setText("#pt-partner-work-state", d.custom_partner_work_state);
        setText("#pt-partner-work-completed", d.custom_partner_work_completed);
        setText("#pt-subject", d.subject);
        setText("#pt-summary", htmlToText(d.summary));
        setText(
          "#pt-partner-acceptance-note",
          d.latest_partner_acceptance_note,
        );
        setText("#pt-partner-work-done-note", d.latest_partner_work_done_note);
        setText(
          "#pt-partner-work-rework-note",
          d.latest_partner_work_rework_note,
        );
        setText(
          "#pt-partner-work-review-note",
          d.latest_partner_work_review_note,
        );
        setText("#pt-partner-review-note", d.latest_partner_review_note);
        setText("#pt-partner-rework-note", d.latest_partner_rework_note);
        setText(
          "#pt-partner-work-review-note",
          d.latest_partner_work_review_note,
        );
        setText(
          "#pt-partner-acceptance-request-note",
          d.latest_partner_acceptance_request_note,
        );
        setText(
          "#pt-partner-acceptance-request-note",
          d.latest_partner_acceptance_request_note,
        );

        const hasAcceptanceNote = Boolean(d.latest_partner_acceptance_note);
        const hasWorkDoneNote = Boolean(d.latest_partner_work_done_note);
        const hasReviewNote = Boolean(d.latest_partner_review_note);
        const hasReworkNote = Boolean(d.latest_partner_rework_note);
        const hasWorkReworkNote = Boolean(d.latest_partner_work_rework_note);
        const hasWorkReviewNote = Boolean(d.latest_partner_work_review_note);
        const hasAcceptanceRequestNote = Boolean(
          d.latest_partner_acceptance_request_note,
        );

        if (
          hasAcceptanceRequestNote ||
          hasAcceptanceNote ||
          hasWorkDoneNote ||
          hasReviewNote ||
          hasReworkNote ||
          hasWorkReworkNote ||
          hasWorkReworkNote ||
          hasWorkReviewNote
        ) {
          $body.find("#pt-partner-notes").show();
        } else {
          $body.find("#pt-partner-notes").hide();
        }

        $body
          .find("#pt-partner-acceptance-note-section")
          .toggle(hasAcceptanceNote);

        $body
          .find("#pt-partner-work-done-note-section")
          .toggle(hasWorkDoneNote);

        $body
          .find("#pt-partner-work-rework-note-section")
          .toggle(hasWorkReworkNote);

        $body
          .find("#pt-partner-work-review-note-section")
          .toggle(hasWorkReviewNote);

        $body
          .find("#pt-partner-acceptance-request-note-section")
          .toggle(hasAcceptanceRequestNote);

        $body
          .find("#pt-partner-acceptance-request-note-section")
          .toggle(hasAcceptanceRequestNote);

        $body.find("#pt-partner-review-note-section").toggle(hasReviewNote);
        $body.find("#pt-partner-rework-note-section").toggle(hasReworkNote);

        showContent();
        updatePartnerAction(d);
        loadAttachments(d.name || ticketName);
        page.set_indicator("");
      },
      error: function (xhr) {
        console.error(xhr);
        showError("Could not load ticket.");
        page.set_indicator("");
      },
    });
  }

  $body.find("#pt-back-submitted").on("click", () => {
    frappe.set_route("query-report", "Tickets Submitted by Partner");
  });

  $body.find("#pt-upload-attachment").on("click", () => {
    const ticketName = getTicketName();

    if (!ticketName) {
      frappe.msgprint("Missing ticket name.");
      return;
    }

    showUploadAttachmentDialog(ticketName);
  });

  $body.find("#pt-back-active").on("click", () => {
    frappe.set_route("query-report", "Tickets Assigned to Partner");
  });

  $body.find("#pt-back-archived").on("click", () => {
    frappe.set_route("query-report", "Partner Archived Tickets");
  });

  $body.find("#pt-request-rework").on("click", () => {
    const ticketName = getTicketName();

    const dialog = new frappe.ui.Dialog({
      title: "Request Rework",
      fields: [
        {
          label: "Reason",
          fieldname: "note",
          fieldtype: "Small Text",
          reqd: 1,
          description: "Please explain what needs to be corrected.",
        },
      ],
      primary_action_label: "Request Rework",
      primary_action(values) {
        if (!values.note || !values.note.trim()) {
          frappe.msgprint("Please enter a rework reason.");
          return;
        }

        frappe.call({
          method: "telephony.partner_create.request_partner_acceptance_rework",
          args: {
            ticket_name: ticketName,
            note: values.note,
          },
          freeze: true,
          freeze_message: "Requesting rework…",
          callback: function () {
            frappe.show_alert({
              message: __("Rework requested for {0}", [ticketName]),
              indicator: "green",
            });

            dialog.hide();
            loadTicket();
          },
          error: function (xhr) {
            console.error(xhr);
            frappe.msgprint({
              title: __("Request failed"),
              message: __("Could not request rework."),
              indicator: "red",
            });
          },
        });
      },
    });

    dialog.show();
  });

  $body.find("#pt-submit-completion").on("click", () => {
    const ticketName = getTicketName();
    const action = $body.find("#pt-submit-completion").data("action");

    const isWorkDone = action === "work-done";

    const dialogTitle = isWorkDone
      ? "Submit Work Done"
      : "Submit Acceptance Note";

    const dateLabel = isWorkDone ? "Completed On" : "Accepted On";

    const noteLabel = isWorkDone ? "Work Done Note" : "Acceptance Note";

    const successMessage = isWorkDone
      ? __("Work done note submitted for {0}", [ticketName])
      : __("Acceptance note submitted for {0}", [ticketName]);

    const errorMessage = isWorkDone
      ? __("Could not submit the work done note.")
      : __("Could not submit the acceptance note.");

    const method = isWorkDone
      ? "telephony.partner_create.submit_partner_work_done_note"
      : "telephony.partner_create.submit_partner_completion_note";

    const dialog = new frappe.ui.Dialog({
      title: dialogTitle,
      fields: [
        {
          label: dateLabel,
          fieldname: "completed_on",
          fieldtype: "Date",
          default: frappe.datetime.get_today(),
        },
        {
          label: noteLabel,
          fieldname: "note",
          fieldtype: "Small Text",
          reqd: 1,
        },
      ],
      primary_action_label: "Submit",
      primary_action(values) {
        frappe.call({
          method,
          args: {
            ticket_name: ticketName,
            note: values.note,
            completed_on: values.completed_on,
          },
          callback: function () {
            frappe.show_alert({
              message: successMessage,
              indicator: "green",
            });

            dialog.hide();
            loadTicket();
          },
          error: function (xhr) {
            console.error(xhr);
            frappe.msgprint({
              title: __("Submit failed"),
              message: errorMessage,
              indicator: "red",
            });
          },
        });
      },
    });

    dialog.show();
  });

  wrapper.partner_ticket_page = {
    loadTicket,
  };

  loadTicket();
};

frappe.pages["partner-ticket"].on_page_show = function (wrapper) {
  wrapper.partner_ticket_page?.loadTicket?.();
};

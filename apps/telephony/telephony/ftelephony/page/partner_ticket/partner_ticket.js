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

              <div id="pt-partner-review-note-section" style="display:none;">
                <h5 class="mb-3">Telectro Review Note</h5>
                <div id="pt-partner-review-note" style="white-space: pre-wrap;"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `);

  function getTicketName() {
    const route = frappe.get_route() || [];
    return route[1];
  }

  function setText(id, value) {
    $body.find(id).text(value || "");
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
    ].forEach((id) => setText(id, ""));

    $body.find("#pt-partner-notes").hide();
    $body.find("#pt-partner-acceptance-note-section").hide();
    $body.find("#pt-partner-work-done-note-section").hide();
    $body.find("#pt-partner-review-note-section").hide();
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
      if (workState === "" || workState === "Assigned to Partner") {
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
        setText("#pt-summary", d.summary);
        setText(
          "#pt-partner-acceptance-note",
          d.latest_partner_acceptance_note,
        );
        setText("#pt-partner-work-done-note", d.latest_partner_work_done_note);
        setText("#pt-partner-review-note", d.latest_partner_review_note);
        setText("#pt-partner-rework-note", d.latest_partner_rework_note);

        const hasAcceptanceNote = Boolean(d.latest_partner_acceptance_note);
        const hasWorkDoneNote = Boolean(d.latest_partner_work_done_note);
        const hasReviewNote = Boolean(d.latest_partner_review_note);
        const hasReworkNote = Boolean(d.latest_partner_rework_note);

        if (
          hasAcceptanceNote ||
          hasWorkDoneNote ||
          hasReviewNote ||
          hasReworkNote
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

        $body.find("#pt-partner-review-note-section").toggle(hasReviewNote);
        $body.find("#pt-partner-rework-note-section").toggle(hasReworkNote);

        showContent();
        updatePartnerAction(d);
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

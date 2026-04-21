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
          <button class="btn btn-default btn-sm" id="pt-back-submitted">Submitted Tickets</button>
          <button class="btn btn-default btn-sm" id="pt-back-active">Active Tickets</button>
          <button class="btn btn-default btn-sm" id="pt-back-archived">Archived Tickets</button>
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
              </tbody>
            </table>
          </div>
        </div>

        <div class="card">
          <div class="card-body">
            <h5 class="mb-3">Subject</h5>
            <div id="pt-subject" class="mb-4 font-weight-bold"></div>

            <h5 class="mb-3">Summary</h5>
            <div id="pt-summary" style="white-space: pre-wrap;"></div>
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
    ].forEach((id) => setText(id, ""));
  }

  function hasPartnerAccepted(d) {
    const state = (d?.custom_partner_acceptance_state || "").trim();
    return state === "Accepted by Partner" || state === "Reviewed by Telectro";
  }

  function updateAcceptanceAction(d) {
    const $btn = $body.find("#pt-submit-completion");

    if (hasPartnerAccepted(d)) {
      $btn.hide();
      return;
    }

    $btn.show();
  }

  function showError(message) {
    $body.find("#pt-submit-completion").hide();
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

        setText("#pt-subject", d.subject);
        setText("#pt-summary", d.summary);

        showContent();
        updateAcceptanceAction(d);
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
    frappe.set_route("query-report", "Partner Submitted Tickets");
  });

  $body.find("#pt-back-active").on("click", () => {
    frappe.set_route("query-report", "Partner Active Tickets");
  });

  $body.find("#pt-back-archived").on("click", () => {
    frappe.set_route("query-report", "Partner Archived Tickets");
  });

  $body.find("#pt-submit-completion").on("click", () => {
    const ticketName = getTicketName();

    const dialog = new frappe.ui.Dialog({
      title: "Submit Acceptance Note",
      fields: [
        {
          label: "Accepted On",
          fieldname: "completed_on",
          fieldtype: "Date",
          default: frappe.datetime.get_today(),
        },
        {
          label: "Acceptance Note",
          fieldname: "note",
          fieldtype: "Small Text",
          reqd: 1,
        },
      ],
      primary_action_label: "Submit",
      primary_action(values) {
        frappe.call({
          method: "telephony.partner_create.submit_partner_completion_note",
          args: {
            ticket_name: ticketName,
            note: values.note,
            completed_on: values.completed_on,
          },
          callback: function (r) {
            frappe.show_alert({
              message: __("Acceptance note submitted for {0}", [ticketName]),
              indicator: "green",
            });

            dialog.hide();
            loadTicket();
          },
          error: function (xhr) {
            console.error(xhr);
            frappe.msgprint({
              title: __("Submit failed"),
              message: __("Could not submit the acceptance Note."),
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

frappe.pages["partner-request"].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: "Partner Request",
    single_column: true,
  });

  const $body = $(wrapper).find(".layout-main-section");
  $body.empty();

  $body.append(`
    <div class="partner-request-page">
      <div class="alert alert-primary mb-4">
        Capture what is needed for a Telectro request. Location-linked fields help identify the object of interest clearly.
      </div>

      <div class="row">
        <div class="col-md-6">
          <div class="form-group mb-3">
            <div id="pr-custom-customer-control"></div>
          </div>

          <div class="form-group mb-3">
            <div id="pr-custom-site-group-control"></div>
          </div>

          <div class="form-group mb-3">
            <label class="control-label">Fault Category</label>
            <select class="form-control" id="pr-custom-fault-category">
              <option value=""></option>
              <option value="Buildings">Buildings</option>
              <option value="Network Nodes">Network Nodes</option>
              <option value="Links">Links</option>
              <option value="Areas">Areas</option>
              <option value="Other">Other</option>
              <option value="Residents">Residents</option>
            </select>
          </div>

          <div class="form-group mb-3">
            <div id="pr-custom-fault-asset-control"></div>
          </div>

          <div class="form-group mb-3">
            <div id="pr-custom-site-control"></div>
          </div>

          <div class="form-group mb-3">
            <label class="control-label">Ownership</label>
            <select class="form-control" id="pr-custom-ownership-model">
              <option value=""></option>
              <option value="Leased (Telectro-owned)">Leased (Telectro-owned)</option>
              <option value="Customer-owned">Customer-owned</option>
              <option value="Unknown / Not sure">Unknown / Not sure</option>
            </select>
          </div>

          <div class="form-group mb-3">
            <label class="control-label">Request Type</label>
            <select class="form-control" id="pr-custom-request-type">
              <option value="General Assistance" selected>General Assistance</option>
              <option value="Access Request">Access Request</option>
              <option value="Quote / Pricing">Quote / Pricing</option>
              <option value="Installation / Move">Installation / Move</option>
              <option value="Partner Follow-up">Partner Follow-up</option>
              <option value="Other">Other</option>
            </select>
          </div>

          <div class="form-group mb-4">
            <label class="control-label">Due Date</label>
            <input type="date" class="form-control" id="pr-custom-due-date">
          </div>
        </div>

        <div class="col-md-6">
          <div class="form-group mb-3">
            <label class="control-label reqd">Subject</label>
            <input
              type="text"
              class="form-control"
              id="pr-subject"
              placeholder='e.g. "Boschendal – Camera offline – Villa"'
            >
          </div>

          <div class="form-group mb-4">
            <label class="control-label">Summary</label>
            <textarea
              class="form-control"
              id="pr-summary"
              rows="14"
              placeholder="Describe the issue, impact, and any useful context."
            ></textarea>
          </div>

          <div class="form-group mb-4">
            <label class="control-label">Add Photo or File</label>
            <input
              type="file"
              class="form-control"
              id="pr-evidence-files"
              accept=".jpg,.jpeg,.png,.pdf,.doc,.docx,.xls,.xlsx,.txt"
              multiple
            >
            <div class="text-muted small mt-2">
              Add field photos, WhatsApp images, quotes, or supporting documents for this request.
              Maximum size: 10 MB. JPG, PNG, PDF, Word, Excel, and text files are supported in V1.
              Files will be stored privately against the created ticket.
            </div>
            <div id="pr-evidence-selected" class="text-muted small mt-2"></div>
          </div>
        </div>
      </div>

      <div class="d-flex gap-2">
        <button class="btn btn-primary" id="pr-submit">Submit Request</button>
      </div>
    </div>
  `);

  const DEFAULTS = {
    custom_fault_category: "Buildings",
    custom_service_area: "Other",
    custom_severity: "Sev3",
    custom_request_type: "General Assistance",
  };

  function getSelectedEvidenceFiles() {
    const input = $body.find("#pr-evidence-files").get(0);
    return Array.from(input?.files || []);
  }

  function renderSelectedEvidenceFiles() {
    const files = getSelectedEvidenceFiles();
    const $selected = $body.find("#pr-evidence-selected");

    if (!files.length) {
      $selected.text("");
      return;
    }

    const names = files.map(
      (file) => `${file.name} (${formatBytes(file.size)})`,
    );

    $selected.text(`Selected: ${names.join(", ")}`);
  }

  function formatBytes(bytes) {
    if (!bytes && bytes !== 0) {
      return "";
    }

    const units = ["B", "KB", "MB", "GB"];
    let size = bytes;
    let unit = 0;

    while (size >= 1024 && unit < units.length - 1) {
      size = size / 1024;
      unit += 1;
    }

    return `${size.toFixed(unit === 0 ? 0 : 1)} ${units[unit]}`;
  }

  function readFileAsDataUrl(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();

      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(reader.error);

      reader.readAsDataURL(file);
    });
  }

  async function uploadPartnerRequestEvidence(ticketName, files) {
    const maxBytes = 10 * 1024 * 1024;

    for (const file of files) {
      if (file.size > maxBytes) {
        frappe.throw(
          __("{0} is too large. Maximum size is 10 MB.", [file.name]),
        );
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
      });
    }
  }

  function geomForCategory(cat) {
    const c = (cat || "").trim();
    if (c === "Links") return "LineString";
    if (c === "Areas") return "Polygon";
    return "Point";
  }

  function isNonPointCategory(cat) {
    const c = (cat || "").trim();
    return c === "Links" || c === "Areas";
  }

  const controls = {
    custom_customer: frappe.ui.form.make_control({
      parent: $body.find("#pr-custom-customer-control"),
      df: {
        fieldtype: "Link",
        options: "Customer",
        fieldname: "custom_customer",
        label: "Customer",
      },
      render_input: true,
    }),
    custom_site_group: frappe.ui.form.make_control({
      parent: $body.find("#pr-custom-site-group-control"),
      df: {
        fieldtype: "Link",
        options: "Location",
        fieldname: "custom_site_group",
        label: "Campus",
      },
      render_input: true,
    }),
    custom_fault_asset: frappe.ui.form.make_control({
      parent: $body.find("#pr-custom-fault-asset-control"),
      df: {
        fieldtype: "Link",
        options: "Location",
        fieldname: "custom_fault_asset",
        label: "Fault Asset",
      },
      render_input: true,
    }),
    custom_site: frappe.ui.form.make_control({
      parent: $body.find("#pr-custom-site-control"),
      df: {
        fieldtype: "Link",
        options: "Location",
        fieldname: "custom_site",
        label: "Fault Point",
      },
      render_input: true,
    }),
  };

  Object.values(controls).forEach((control) => control.refresh());

  function getValue(fieldname) {
    if (controls[fieldname]) return controls[fieldname].get_value();
    return "";
  }

  async function mapCustomerToCampus() {
    const customer = getValue("custom_customer");
    if (!customer) return;

    try {
      const r = await frappe.db.get_value(
        "Customer",
        customer,
        "custom_default_campus",
      );
      const campus = r?.message?.custom_default_campus;
      if (campus && campus !== getValue("custom_site_group")) {
        controls.custom_site_group.set_value(campus);
      }
    } catch (e) {
      console.warn("Could not map customer to campus", e);
    }
  }

  function applyCampusLock() {
    const hasCustomer = !!getValue("custom_customer");
    const hasCampus = !!getValue("custom_site_group");
    const shouldLock = hasCustomer && hasCampus;

    controls.custom_site_group.df.read_only = shouldLock ? 1 : 0;
    controls.custom_site_group.df.description = shouldLock
      ? "Auto-set from Customer"
      : "";

    controls.custom_site_group.refresh();
  }

  function clearDependentSelections() {
    controls.custom_fault_asset.set_value("");
    controls.custom_site.set_value("");
  }

  function applyDefaults() {
    const $faultCategory = $body.find("#pr-custom-fault-category");
    const $requestType = $body.find("#pr-custom-request-type");

    if (!$faultCategory.val()) {
      $faultCategory.val(DEFAULTS.custom_fault_category);
    }

    if (!$requestType.val()) {
      $requestType.val(DEFAULTS.custom_request_type);
    }
  }

  function setQueries() {
    controls.custom_site_group.get_query = () => ({
      filters: { parent_location: "Pilot Sites", is_group: 1 },
      page_length: 50,
    });

    controls.custom_site.get_query = () => {
      const campus = getValue("custom_site_group");
      const cat = $body.find("#pr-custom-fault-category").val();

      if (!campus || !cat) {
        return { filters: { name: "__never__" } };
      }

      return {
        filters: {
          parent_location: `${campus} - ${cat}`,
          is_group: 0,
          custom_kmz_geometry_type: "Point",
        },
        page_length: 50,
      };
    };

    controls.custom_fault_asset.get_query = () => {
      const campus = getValue("custom_site_group");
      const cat = $body.find("#pr-custom-fault-category").val();

      if (!campus || !cat) {
        return { filters: { name: "__never__" } };
      }

      return {
        filters: {
          parent_location: `${campus} - ${cat}`,
          is_group: 0,
          custom_kmz_geometry_type: geomForCategory(cat),
        },
        page_length: 50,
      };
    };
  }

  function syncPointFields() {
    const cat = $body.find("#pr-custom-fault-category").val();
    const nonPoint = isNonPointCategory(cat);

    if (!nonPoint) {
      const point = getValue("custom_site");
      const asset = getValue("custom_fault_asset");
      if (point && asset !== point) {
        controls.custom_fault_asset.set_value(point);
      }
    } else {
      if (getValue("custom_site")) {
        controls.custom_site.set_value("");
      }
    }
  }

  async function onCustomerChanged() {
    clearDependentSelections();

    $body.find("#pr-custom-fault-category").val("");
    applyDefaults();

    controls.custom_site_group.set_value("");

    await mapCustomerToCampus();
    applyCampusLock();
    setQueries();
  }

  function onCampusChanged() {
    clearDependentSelections();
    applyDefaults();
    setQueries();
    applyCampusLock();
  }

  function onFaultCategoryChanged() {
    clearDependentSelections();
    setQueries();
    syncPointFields();
  }

  controls.custom_customer.$input.on("change", async () => {
    await onCustomerChanged();
  });

  controls.custom_site_group.$input.on("change", () => {
    onCampusChanged();
  });

  controls.custom_site.$input.on("change", () => {
    syncPointFields();
  });

  $body.find("#pr-custom-fault-category").on("change", () => {
    onFaultCategoryChanged();
  });

  applyDefaults();
  setQueries();
  applyCampusLock();

  $body.find("#pr-submit").on("click", async () => {
    const subject = ($body.find("#pr-subject").val() || "").trim();
    let summary = ($body.find("#pr-summary").val() || "").trim();

    if (!subject) {
      frappe.msgprint("Subject is required");
      return;
    }

    if (!summary) {
      summary = subject;
    }

    const payload = {
      custom_customer: getValue("custom_customer"),
      custom_site_group: getValue("custom_site_group"),
      custom_fault_category: $body.find("#pr-custom-fault-category").val(),
      custom_fault_asset: getValue("custom_fault_asset"),
      custom_site: getValue("custom_site"),
      custom_ownership_model: $body.find("#pr-custom-ownership-model").val(),
      subject,
      summary,
      custom_request_type: $body.find("#pr-custom-request-type").val(),
      custom_due_date: $body.find("#pr-custom-due-date").val(),
      custom_service_area: DEFAULTS.custom_service_area,
      custom_severity: DEFAULTS.custom_severity,
      ticket_type: "Service Request",
    };

    page.set_indicator("Submitting…", "blue");
    $body.find("#pr-submit").prop("disabled", true);

    $body.find("#pr-evidence-files").on("change", () => {
      renderSelectedEvidenceFiles();
    });

    try {
      const evidenceFiles = getSelectedEvidenceFiles();

      const r = await frappe.call({
        method: "telephony.partner_create.create_partner_ticket",
        args: payload,
      });

      const ticketName = r.message?.name;

      if (!ticketName) {
        throw new Error(
          "Partner request was created, but no ticket name was returned.",
        );
      }

      if (evidenceFiles.length) {
        page.set_indicator("Uploading evidence…", "blue");

        try {
          await uploadPartnerRequestEvidence(ticketName, evidenceFiles);
        } catch (uploadError) {
          console.error(uploadError);

          frappe.msgprint({
            title: __("Request submitted, evidence upload failed"),
            message: __(
              "The request {0} was created, but one or more files could not be uploaded. Please open the Partner Ticket and add the files there.",
              [ticketName],
            ),
            indicator: "orange",
          });

          frappe.set_route("partner-ticket", ticketName);
          return;
        }
      }

      frappe.show_alert(
        {
          message: evidenceFiles.length
            ? __("Partner request submitted with evidence: {0}", [ticketName])
            : __("Partner request submitted: {0}", [ticketName]),
          indicator: "green",
        },
        7,
      );

      frappe.set_route("query-report", "Partner Submitted Tickets");
    } catch (e) {
      console.error(e);
      frappe.msgprint({
        title: __("Submit failed"),
        message: e?.message || __("Could not submit the Partner request."),
        indicator: "red",
      });
    } finally {
      page.set_indicator("");
      $body.find("#pr-submit").prop("disabled", false);
    }
  });
};

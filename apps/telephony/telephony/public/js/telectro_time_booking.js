(() => {
  const api = "telephony.api.time_booking.";
  const corrections = "telephony.api.booking_correction.";
  const technicianRole = "TELECTRO-POC Role - Tech";
  const dateFormat = "YYYY-MM-DD HH:mm:ss";
  const bookingErrorCodes = new Set([
    "original_creation_exceeded", "invalid_ticket_interval", "invalid_booking", "booking_access_denied",
    "booking_reference_denied", "booking_overlap", "booking_changed", "booking_linked",
  ]);

  const get = async (method, args) =>
    (await frappe.call({ method: api + method, type: "GET", args })).message;

  async function post(method, args) {
    // Keep Emergency and Duration numeric when Frappe parses the request.
    const response = await fetch("/api/method/" + method, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        "X-Frappe-CSRF-Token": frappe.csrf_token,
      },
      body: JSON.stringify(args),
    });
    if (!response.ok) {
      const fallback = __("Unable to save the booking. Check the details and try again.");
      let error;
      if (response.status >= 400 && response.status < 500) {
        const body = await response.json().catch(() => null);
        error = body?.error;
      }
      if (bookingErrorCodes.has(error?.code) && typeof error.message === "string") {
        throw new Error(frappe.utils.escape_html(error.message));
      }
      throw new Error(fallback);
    }
    return (await response.json()).message;
  }

  function preCreationText(value) {
    if (!Number.isSafeInteger(value) || value < 0 || value > 86400000000) {
      return __("Pre-creation portion: not established.");
    }
    const seconds = Math.floor(value / 1000000);
    const fraction = String(value % 1000000).padStart(6, "0").replace(/0+$/, "");
    const duration = fraction ? `${seconds}.${fraction}` : String(seconds);
    return __("Pre-creation portion: {0} seconds, included in total booked time.", [duration]);
  }

  function showError(message) {
    frappe.msgprint({ title: __("Time Booking"), message, indicator: "orange" });
  }

  function correctionDetails(booking, reason) {
    return {
      timesheet_name: booking.name,
      expected_modified: booking.modified,
      event_id: Array.from(crypto.getRandomValues(new Uint32Array(4)),
        (part) => part.toString(16).padStart(8, "0")).join(""),
      reason: reason.trim(),
    };
  }

  function correctionRequest(dialog, booking, method, args, afterSave) {
    const button = dialog.get_primary_btn();
    let previous;
    return async (values) => {
      if (!values.reason?.trim() || values.reason.trim().length > 2000) {
        showError(__("Enter a correction reason of up to 2,000 characters."));
        return;
      }
      if (button.prop("disabled")) return;
      const payload = args(values);
      if (!payload) return;
      const key = JSON.stringify([payload, values.reason.trim()]);
      if (previous?.key !== key) {
        previous = { key, details: correctionDetails(booking, values.reason) };
      }
      button.prop("disabled", true);
      try {
        await post(corrections + method, { ...payload, ...previous.details });
        dialog.hide();
        frappe.show_alert({ message: __("Time booking updated."), indicator: "green" });
        afterSave();
      } catch (error) {
        showError(error.message);
      } finally {
        button.prop("disabled", false);
      }
    };
  }

  function bookingPayload(values, ticketArea, options) {
    const description = values.description?.trim();
    const duration = String(values.duration_minutes ?? "");
    const now = frappe.datetime.system_datetime();
    if (
      !description || description.length > 2000 || !values.from_time ||
      !moment(values.from_time, dateFormat, true).isValid() ||
      values.from_time > now || !/^[1-9][0-9]{0,3}$/.test(duration) ||
      Number(duration) > 1440
    ) {
      showError(__("Enter a start time at or before now, 1 to 1,440 whole minutes, and a description of up to 2,000 characters."));
      return null;
    }

    const payload = {
      work_context: values.work_context,
      from_time: values.from_time,
      duration_minutes: Number(duration),
      description,
      activity_type: values.activity_type,
      emergency: values.emergency === "Yes" ? 1 : 0,
      work_origin: values.work_origin,
    };

    if (values.activity_type !== "Travel") {
      payload.work_location = values.work_location;
    }
    if (values.work_context === "Helpdesk") {
      const ticket = String(values.ticket_name ?? "");
      if (ticketArea?.ticket !== ticket || !options.service_areas.includes(ticketArea.area)) {
        showError(__("Select a readable Helpdesk ticket with a valid Service Area."));
        return null;
      }
      payload.ticket_name = ticket;
      payload.service_area = ticketArea.area;
    } else if (values.service_area) {
      payload.service_area = values.service_area;
    }
    if (values.work_context === "Project") {
      payload.project_name = values.project_name;
      if (values.task_name) payload.task_name = values.task_name;
    }
    if (values.work_context !== "Internal" && values.customer_name) {
      payload.customer_name = values.customer_name;
    }
    if (values.work_context === "Customer Support" && !values.customer_name) {
      payload.unlisted_customer_name = values.unlisted_customer_name?.trim();
      if (!payload.unlisted_customer_name) {
        showError(__("Enter the unlisted customer name or select a customer."));
        return null;
      }
    }
    if (values.work_origin === "Snapfix") {
      payload.external_reference = values.external_reference?.trim();
      if (!payload.external_reference) {
        showError(__("Enter the Snapfix reference."));
        return null;
      }
    }
    if (values.work_origin === "Other") {
      payload.other_origin_description = values.other_origin_description?.trim();
      if (!payload.other_origin_description) {
        showError(__("Describe where the work originated."));
        return null;
      }
    }
    return payload;
  }

  function completedWorkInterval(values) {
    const start = values.from_time;
    const duration = String(values.duration_minutes ?? "");
    if (!start || !/^[1-9][0-9]{0,3}$/.test(duration) || Number(duration) > 1440) return null;
    // Compute site-local wall time without applying the browser's timezone or DST rules.
    const end = moment.utc(start, dateFormat, true);
    if (!end.isValid() || end.add(Number(duration), "minutes").format(dateFormat) >
        frappe.datetime.system_datetime()) return null;
    return { from_time: start, duration_minutes: Number(duration) };
  }

  function openForm(options, booking, afterSave) {
    const inHelpdesk = (values) => values.work_context === "Helpdesk";
    const inProject = (values) => values.work_context === "Project";
    const needsLocation = (values) => !!values.activity_type && values.activity_type !== "Travel";
    const needsUnlisted = (values) => values.work_context === "Customer Support" && !values.customer_name;
    const snapfix = (values) => values.work_origin === "Snapfix";
    const otherOrigin = (values) => values.work_origin === "Other";
    const selectOptions = (values) => ["", ...values];
    const previousActivity = booking?.activity_type;
    const historicalActivity = previousActivity && !options.activity_types.includes(previousActivity);

    let ticketLookup = 0;
    let ticketArea;
    let customerLookup = 0;
    let customerReference;
    let customerPreview;
    let dialog;
    let restoring = Boolean(booking);
    let projectContext = booking?.work_context === "Project";
    let periodRevision = 0;
    let periodKey;
    const referenceRevision = { project_name: 0, task_name: 0 };
    const referenceOptions = {};
    const projectField = "project_name";
    const taskField = "task_name";

    function referenceScope(field, values) {
      if (!inProject(values)) return null;
      const interval = completedWorkInterval(values);
      if (!interval) return null;
      if (field === projectField) return interval;
      return values.project_name ? { ...interval, project_name: values.project_name } : null;
    }

    const currentScope = (field) => referenceScope(field, {
      work_context: dialog.get_value("work_context"),
      from_time: dialog.get_value("from_time"),
      duration_minutes: dialog.get_value("duration_minutes"),
      project_name: dialog.get_value(projectField),
    });

    function renderReferences(field, items, selected) {
      const control = dialog.fields_dict[field];
      control.df.options = ["", ...items.map(({ id, label }) => ({
        value: id,
        label: frappe.utils.escape_html(label === id ? id : label + " (" + id + ")"),
      }))];
      control.set_options();
      if (selected) control.$input.val(selected);
    }

    function clearReference(field) {
      referenceRevision[field]++;
      delete referenceOptions[field];
      renderReferences(field, []);
      return dialog.set_value(field, "");
    }

    async function loadReferences(field, name) {
      const revision = ++referenceRevision[field];
      const scope = currentScope(field);
      if (!scope) return false;
      const key = JSON.stringify(scope);
      const isProject = field === projectField;
      const search = name ? { name } : {
        query: (dialog.get_value(isProject ? "project_search" : "task_search") || "").slice(0, 80),
      };
      let items;
      try {
        items = await get(isProject ? "get_booking_projects" : "get_booking_tasks", { ...scope, ...search });
      } catch {
        items = [];
      }
      if (revision !== referenceRevision[field] || key !== JSON.stringify(currentScope(field))) return false;

      const selected = dialog.get_value(field);
      const previous = referenceOptions[field];
      const retained = previous?.key === key && previous.items.find((item) => item.id === selected);
      items = Array.isArray(items) ? items : [];
      if (retained && !items.some((item) => item.id === retained.id)) items = [retained, ...items];
      referenceOptions[field] = { key, items };
      renderReferences(field, items, retained?.id);
      if (name && items.some((item) => item.id === name)) {
        await dialog.set_value(field, name);
        return true;
      }
      return false;
    }

    async function periodChanged() {
      if (restoring) return;
      const inScope = dialog.get_value("work_context") === "Project";
      if (!projectContext && !inScope) return;
      const key = JSON.stringify(currentScope(projectField));
      if (projectContext === inScope && periodKey === key) return;
      projectContext = inScope;
      periodKey = key;
      const revision = ++periodRevision;
      await Promise.all([clearReference(taskField), clearReference(projectField)]);
      if (revision === periodRevision) await loadReferences(projectField);
    }

    async function projectChanged() {
      if (restoring) return;
      const revision = referenceRevision[taskField] + 1;
      await clearReference(taskField);
      if (revision !== referenceRevision[taskField]) return;
      if (dialog.get_value("task_search")) {
        // Clearing a nonempty search triggers the Task lookup.
        await dialog.set_value("task_search", "");
      } else {
        await loadReferences(taskField);
      }
    }

    function linkedCustomer(values) {
      if (inHelpdesk(values) && values.ticket_name) {
        return { ticket_name: String(values.ticket_name) };
      }
      if (inProject(values) && values.project_name) {
        const interval = completedWorkInterval(values);
        if (interval) return { ...interval, project_name: values.project_name };
      }
      return null;
    }

    async function updateCustomer() {
      const values = Object.fromEntries(
        ["work_context", "ticket_name", projectField, "from_time", "duration_minutes"]
          .map((name) => [name, dialog.get_value(name)]),
      );
      const reference = linkedCustomer(values);
      const key = JSON.stringify(reference);
      if (customerReference === key) return;
      const hadReference = customerReference && customerReference !== "null";
      customerReference = key;
      const revision = ++customerLookup;
      customerPreview = null;
      if (reference || hadReference) await dialog.set_value("customer_name", "");
      if (revision !== customerLookup) return;
      if (!reference) {
        await dialog.set_value("derived_customer", "");
        dialog.refresh_dependency();
        return;
      }
      const historical = booking?.work_context === values.work_context && (
        inHelpdesk(values) ? String(booking.ticket_name) === reference.ticket_name
          : booking.project_name === reference.project_name
      );
      await dialog.set_value("derived_customer", __("Loading…"));
      dialog.refresh_dependency();
      let preview;
      try {
        preview = historical
          ? { customer_name: booking.customer_name, historical: true }
          : await get("get_booking_reference_customer", reference);
      } catch {
        preview = { configuration_error: __("Customer could not be resolved for this reference.") };
      }
      if (revision !== customerLookup) return;
      customerPreview = preview;
      await dialog.set_value("derived_customer",
        preview.configuration_error || preview.customer_name || __("No Customer recorded."));
      dialog.refresh_dependency();
    }

    const maySelectCustomer = (values) => values.work_context === "Customer Support" || (
      inHelpdesk(values) && linkedCustomer(values) && customerPreview
      && !customerPreview.customer_name && !customerPreview.historical && !customerPreview.configuration_error
    );

    function formPayload(values) {
      if (inProject(values)) {
        for (const field of [projectField, taskField]) {
          if (field === taskField && !values.task_name) continue;
          const key = JSON.stringify(referenceScope(field, values));
          const choices = referenceOptions[field];
          if (choices?.key !== key || !choices.items.some((item) => item.id === values[field])) {
            showError(__("Select an eligible Project and optional Task for the completed work interval."));
            return null;
          }
        }
      }
      const reference = linkedCustomer(values);
      if (reference && (customerReference !== JSON.stringify(reference) || !customerPreview
          || customerPreview.configuration_error)) {
        showError(customerPreview?.configuration_error || __("Wait for the Customer to load."));
        return null;
      }
      const customerName = maySelectCustomer(values) ? values.customer_name : undefined;
      return bookingPayload({ ...values, customer_name: customerName }, ticketArea, options);
    }

    async function updateTicketArea() {
      const revision = ++ticketLookup;
      const ticket = String(dialog.get_value("ticket_name") ?? "");
      ticketArea = null;
      if (dialog.get_value("work_context") !== "Helpdesk" || !ticket) {
        await dialog.set_value("ticket_area", "");
        return;
      }
      await dialog.set_value("ticket_area", __("Loading…"));
      try {
        const result = await get("get_booking_ticket_area", { ticket_name: ticket });
        if (revision !== ticketLookup) return;
        if (options.service_areas.includes(result?.service_area)) {
          ticketArea = { ticket, area: result.service_area };
        }
        await dialog.set_value(
          "ticket_area",
          ticketArea?.area || __("The ticket needs a Service Area."),
        );
      } catch {
        if (revision === ticketLookup) {
          await dialog.set_value("ticket_area", __("Service Area could not be loaded."));
        }
      }
    }

    const fields = [
      {
        fieldname: "work_context", label: __("Work Context"), fieldtype: "Select",
        options: selectOptions(["Helpdesk", "Project", "Customer Support", "Internal"]),
        reqd: 1,
        onchange: () => dialog && Promise.all([updateTicketArea(), periodChanged(), updateCustomer()]),
      },
      {
        fieldname: "ticket_name", label: __("Helpdesk Ticket"), fieldtype: "Link",
        options: "HD Ticket", depends_on: inHelpdesk, mandatory_depends_on: inHelpdesk,
        get_query: () => ({ query: api + "search_booking_tickets" }),
        onchange: () => dialog && Promise.all([updateTicketArea(), updateCustomer()]),
      },
      {
        fieldname: "project_search", label: __("Find Project"), fieldtype: "Data", length: 80,
        depends_on: (values) => inProject(values) && !!completedWorkInterval(values),
        onchange: () => dialog && !restoring && loadReferences(projectField),
      },
      {
        fieldname: projectField, label: __("Project"), fieldtype: "Select", options: [""],
        depends_on: inProject, mandatory_depends_on: inProject,
        description: __("Enter a completed work interval to load eligible Projects. Refine the search if needed."),
        onchange: () => dialog && Promise.all([projectChanged(), updateCustomer()]),
      },
      {
        fieldname: "task_search", label: __("Find Task"), fieldtype: "Data", length: 80,
        depends_on: (values) => inProject(values) && !!values.project_name,
        onchange: () => dialog && !restoring && loadReferences(taskField),
      },
      {
        fieldname: taskField, label: __("Task"), fieldtype: "Select", options: [""],
        depends_on: (values) => inProject(values) && !!values.project_name,
      },
      {
        fieldname: "customer_name", label: __("Customer"), fieldtype: "Link",
        options: "HD Customer",
        depends_on: maySelectCustomer,
      },
      {
        fieldname: "derived_customer", label: __("Customer from Ticket or Project"), fieldtype: "Data",
        read_only: 1, depends_on: (values) => linkedCustomer(values) && !maySelectCustomer(values),
      },
      {
        fieldname: "unlisted_customer_name", label: __("Unlisted Customer Name"), fieldtype: "Data",
        depends_on: needsUnlisted, mandatory_depends_on: needsUnlisted,
      },
      { fieldtype: "Column Break" },
      {
        fieldname: "service_area", label: __("Service Area"), fieldtype: "Select",
        options: selectOptions(options.service_areas),
        depends_on: (values) => !!values.work_context && !inHelpdesk(values),
        mandatory_depends_on: (values) =>
          inProject(values) || values.work_context === "Customer Support",
      },
      {
        fieldname: "ticket_area", label: __("Service Area from Ticket"), fieldtype: "Data",
        read_only: 1, depends_on: inHelpdesk,
      },
      {
        fieldname: "activity_type", label: __("Activity Type"), fieldtype: "Select",
        options: selectOptions(options.activity_types), reqd: 1,
        description: historicalActivity
          ? __("Previous Activity Type: {0}. Select an approved Activity Type to save.", [
            frappe.utils.escape_html(previousActivity),
          ])
          : undefined,
      },
      {
        fieldname: "work_location", label: __("Work Location"), fieldtype: "Select",
        options: selectOptions(options.work_locations),
        depends_on: needsLocation, mandatory_depends_on: needsLocation,
      },
      {
        fieldname: "work_origin", label: __("Work Origin"), fieldtype: "Select",
        options: selectOptions(options.work_origins), reqd: 1,
      },
      {
        fieldname: "external_reference", label: __("Snapfix Reference"), fieldtype: "Data",
        depends_on: snapfix, mandatory_depends_on: snapfix,
      },
      {
        fieldname: "other_origin_description", label: __("Other Origin Description"), fieldtype: "Small Text",
        depends_on: otherOrigin, mandatory_depends_on: otherOrigin,
      },
      {
        fieldname: "emergency", label: __("Emergency / Unplanned"), fieldtype: "Select",
        options: selectOptions(["No", "Yes"]), reqd: 1,
      },
      { fieldtype: "Section Break" },
      {
        fieldname: "from_time", label: __("Start Date and Time"), fieldtype: "Datetime", reqd: 1,
        options: { startDate: frappe.datetime.now_datetime(true) },
        onchange: () => dialog && periodChanged(),
      },
      { fieldtype: "Column Break" },
      {
        fieldname: "duration_minutes", label: __("Duration (minutes)"), fieldtype: "Data", reqd: 1,
        onchange: () => dialog && periodChanged(),
      },
      { fieldtype: "Section Break" },
      { fieldname: "description", label: __("Description"), fieldtype: "Small Text", reqd: 1 },
    ];
    if (booking) {
      if (booking.work_context === "Helpdesk") {
        fields.push({ fieldname: "saved_pre_creation", fieldtype: "HTML" });
      }
      fields.push({ fieldname: "reason", label: __("Correction Reason"), fieldtype: "Small Text", reqd: 1 });
    }
    const replacing = booking?.docstatus === 1;
    dialog = new frappe.ui.Dialog({
      title: replacing ? __("Replace Submitted Booking") : booking ? __("Correct Draft Booking") : __("Book Time"),
      fields,
      size: "large",
      no_submit_on_enter: true,
      primary_action_label: __("Save Booking"),
      primary_action: async (values) => {
        const payload = formPayload(values);
        if (!payload) return;
        const button = dialog.get_primary_btn();
        if (button.prop("disabled")) return;
        button.prop("disabled", true);
        try {
          const result = await post(api + "book_technician_time", payload);
          dialog.hide();
          const saved = __("Draft booking {0} saved.", [result.timesheet]);
          frappe.show_alert({
            message: payload.work_context === "Helpdesk"
              ? `${saved} ${preCreationText(result.pre_creation_us)}`
              : saved,
            indicator: "green",
          });
          afterSave();
        } catch (error) {
          showError(error.message);
        } finally {
          button.prop("disabled", false);
        }
      },
    });
    dialog.fields_dict.duration_minutes.$input.attr("inputmode", "numeric");
    if (dialog.fields_dict.saved_pre_creation) {
      dialog.fields_dict.saved_pre_creation.$wrapper.text(
        __("Saved booking: {0}", [preCreationText(booking.pre_creation_us)]),
      );
    }
    if (booking) {
      dialog.set_primary_action(
        replacing ? __("Replace Booking") : __("Save Correction"),
        correctionRequest(
          dialog, booking, replacing ? "replace_submitted_booking" : "correct_draft_booking",
          formPayload, afterSave,
        ),
      );
    }
    dialog.$wrapper.one("hidden.bs.modal", () => {
      periodRevision++;
      customerLookup++;
      referenceRevision[projectField]++;
      referenceRevision[taskField]++;
      dialog.$wrapper.remove();
    });
    dialog.show();

    if (booking) {
      const button = dialog.get_primary_btn();
      button.prop("disabled", true);
      const fill = async () => {
        for (const field of fields) {
          const key = field.fieldname;
          if (key === projectField || key === taskField || (key === "activity_type" && historicalActivity)
              || (key === "customer_name" && (inHelpdesk(booking) || inProject(booking)))) continue;
          if (key === "emergency" && booking.emergency != null) {
            await dialog.set_value(key, booking.emergency ? "Yes" : "No");
          } else if (key && booking[key] != null) {
            await dialog.set_value(key, booking[key]);
          }
        }
        if (booking.work_context === "Project") {
          const restored = booking.project_name && await loadReferences(projectField, booking.project_name);
          const taskRestored = !booking.task_name || (
            restored && await loadReferences(taskField, booking.task_name)
          );
          await Promise.all([loadReferences(projectField), loadReferences(taskField)]);
          if (!restored || !taskRestored) {
            showError(__("Some saved references are unavailable for this work interval. Review the Project and Task."));
          }
        }
        dialog.refresh_dependency();
      };
      fill()
        .catch(() => showError(__("Some saved details could not be loaded. Check the fields before saving.")))
        .finally(() => {
          restoring = false;
          periodKey = JSON.stringify(currentScope(projectField));
          button.prop("disabled", false);
        });
    }
  }

  function openSavedWork(booking, afterSave) {
    const replacing = booking.docstatus === 1;
    const fields = [
      { fieldname: "description", label: __("Description"), fieldtype: "Small Text", reqd: 1,
        default: booking.description },
      { fieldname: "reason", label: __("Correction Reason"), fieldtype: "Small Text", reqd: 1 },
    ];
    if (booking.work_context === "Helpdesk") {
      fields.push(
        { fieldname: "change_interval", label: __("Change work interval"), fieldtype: "Check" },
        { fieldname: "from_time", label: __("Start (Site Time)"), fieldtype: "Data",
          description: __("Enter YYYY-MM-DD HH:mm:ss, with optional fractional seconds."),
          default: booking.from_time, depends_on: "change_interval", mandatory_depends_on: "change_interval" },
        { fieldname: "duration_minutes", label: __("Duration (minutes)"), fieldtype: "Int",
          default: booking.duration_minutes, depends_on: "change_interval",
          mandatory_depends_on: "change_interval" },
      );
    }
    const dialog = new frappe.ui.Dialog({
      title: replacing ? __("Replace Booking with Saved Reference") : __("Correct Saved Work"),
      fields,
      no_submit_on_enter: true,
    });
    dialog.set_primary_action(
      replacing ? __("Replace Booking") : __("Save Correction"),
      correctionRequest(
        dialog, booking, replacing ? "replace_submitted_booking" : "correct_draft_booking",
        (values) => {
          const description = values.description?.trim();
          if (!description || description.length > 2000) {
            showError(__("Enter a description of up to 2,000 characters."));
            return null;
          }
          const payload = { saved_work: true, description };
          if (values.change_interval) {
            const start = values.from_time?.trim();
            const minutes = Number(values.duration_minutes);
            if (!/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(\.\d{1,6})?$/.test(start)
                || !Number.isInteger(minutes) || minutes < 1 || minutes > 1440) {
              showError(__("Enter the site-local start and a duration of 1 to 1,440 whole minutes."));
              return null;
            }
            Object.assign(payload, { from_time: start, duration_minutes: minutes });
          }
          return payload;
        },
        afterSave,
      ),
    );
    dialog.$wrapper.one("hidden.bs.modal", () => dialog.$wrapper.remove());
    dialog.show();
  }

  function openCancellation(booking, afterSave) {
    const submitted = booking.docstatus === 1;
    const label = submitted ? __("Cancel Booking") : __("Withdraw Draft");
    const dialog = new frappe.ui.Dialog({
      title: label,
      fields: [{ fieldname: "reason", label: __("Reason"), fieldtype: "Small Text", reqd: 1 }],
    });
    dialog.set_primary_action(
      label,
      correctionRequest(
        dialog, booking, submitted ? "cancel_submitted_booking" : "withdraw_draft_booking",
        () => ({}), afterSave,
      ),
    );
    dialog.$wrapper.one("hidden.bs.modal", () => dialog.$wrapper.remove());
    dialog.show();
  }

  function openBookings(options) {
    const dialog = new frappe.ui.Dialog({
      title: __("My Time Bookings"),
      size: "large",
      primary_action_label: __("Book Time"),
      primary_action: () => openForm(options, null, () => load(0)),
      fields: [{ fieldtype: "HTML", fieldname: "bookings" }],
    });
    const output = dialog.fields_dict.bookings.$wrapper;

    function action(label, callback, parent) {
      $("<button>", {
        type: "button", class: "btn btn-default btn-sm mr-2 mb-1", text: label,
      }).on("click", callback).appendTo(parent);
    }

    async function load(start) {
      output.empty().text(__("Loading bookings…"));
      try {
        const page = await get("list_own_bookings", { start });
        output.empty();
        if (!page.bookings.length) {
          $("<p>", { text: __("No time bookings on this page.") }).appendTo(output);
        }
        for (const booking of page.bookings) {
          const item = $("<div>", { class: "border-bottom pb-2 mb-2" }).appendTo(output);
          $("<div>", {
            class: "font-weight-bold mb-1",
            text: __("{0} · {1} minutes · {2}", [
              frappe.datetime.str_to_user(booking.from_time), booking.duration_minutes, booking.work_context,
            ]),
          }).appendTo(item);
          const status = [__("Draft"), __("Submitted"), __("Cancelled")][booking.docstatus];
          $("<div>", { class: "text-muted mb-1", text: [booking.name, status, booking.activity_type].join(" · ") }).appendTo(item);
          $("<p>", { class: "mb-2 text-break", text: booking.description }).appendTo(item);
          if (booking.work_context === "Helpdesk") {
            $("<p>", { class: "text-muted mb-2", text: preCreationText(booking.pre_creation_us) }).appendTo(item);
          }
          if (booking.docstatus !== 2) {
            if (booking.work_context === "Helpdesk" || booking.work_context === "Project") {
              action(__("Correct Saved Work"), () => openSavedWork(booking, () => load(start)), item);
            }
            action(
              booking.docstatus === 0 ? __("Correct Draft") : __("Replace Booking"),
              () => openForm(options, booking, () => load(start)), item,
            );
            action(
              booking.docstatus === 0 ? __("Withdraw Draft") : __("Cancel Booking"),
              () => openCancellation(booking, () => load(start)), item,
            );
          }
        }
        if (page.previous_start != null) action(__("Previous"), () => load(page.previous_start), output);
        if (page.next_start != null) action(__("Next"), () => load(page.next_start), output);
      } catch {
        output.empty().text(__("Unable to load your time bookings."));
        action(__("Retry"), () => load(start), output);
      }
    }

    dialog.$wrapper.one("hidden.bs.modal", () => dialog.$wrapper.remove());
    dialog.show();
    load(0);
  }

  async function installEntryPoint() {
    const toolbar = document.querySelector("header.navbar .navbar-home");
    if (!toolbar || document.getElementById("telectro-time-bookings") ||
        frappe.boot?.read_only || !frappe.user_roles?.includes(technicianRole)) return;

    try {
      const options = await get("get_booking_form");
      if (!Array.isArray(options?.activity_types) ||
          document.getElementById("telectro-time-bookings")) return;
      const launch = () => openBookings(options);
      const launchButton = (id, classes) => $("<button>", {
        id,
        type: "button",
        class: "btn btn-default btn-sm text-nowrap " + classes,
        text: __("Book Time"),
      }).on("click", launch);

      launchButton("telectro-time-bookings", "mr-2")
        .css("margin-inline-start", "var(--margin-sm)").insertAfter(toolbar);

      const mountWorkspaceAction = () => {
        if (frappe.workspace?._page?.name !== "TELECTRO-POC Tech") return;

        const heading = frappe.workspace.editor?.blocks?.getById("oNqAjqwmUa")?.holder;
        const content = heading?.querySelector(".ce-block__content");
        const title = content?.querySelector(".ce-header:not([contenteditable=true])");
        if (!title || content.querySelector("#telectro-workspace-book-time")) return;

        // Keep the action outside the saved heading HTML and let this block grow to fit it.
        content.style.height = "auto";
        launchButton("telectro-workspace-book-time", "mt-2").insertAfter(title);
      };

      const observeWorkspace = () => {
        const editor = document.querySelector("#page-Workspaces .editor-js-container");
        if (!editor) return;

        $(document).off("page-change", observeWorkspace);
        // Workspace blocks render asynchronously and are replaced when switching Workspaces.
        new MutationObserver(mountWorkspaceAction).observe(editor, { childList: true, subtree: true });
        mountWorkspaceAction();
      };

      $(document).on("page-change", observeWorkspace);
      observeWorkspace();
    } catch {
      // Booking availability must not interrupt Desk startup.
    }
  }

  $(document).on("app_ready", installEntryPoint);
  $(installEntryPoint);
})();

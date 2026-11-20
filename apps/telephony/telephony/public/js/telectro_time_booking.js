(() => {
  const api = "telephony.api.time_booking.";
  const corrections = "telephony.api.booking_correction.";
  const technicianRole = "TELECTRO-POC Role - Tech";
  const dateFormat = "YYYY-MM-DD HH:mm:ss";

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
      throw new Error(__("Unable to save the booking. Check the details and try again."));
    }
    return (await response.json()).message;
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
    let dialog;
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
        onchange: () => dialog && updateTicketArea(),
      },
      {
        fieldname: "ticket_name", label: __("Helpdesk Ticket"), fieldtype: "Link",
        options: "HD Ticket", depends_on: inHelpdesk, mandatory_depends_on: inHelpdesk,
        onchange: () => dialog && updateTicketArea(),
      },
      {
        fieldname: "project_name", label: __("Project"), fieldtype: "Link",
        options: "Project", depends_on: inProject, mandatory_depends_on: inProject,
        get_query: () => ({ filters: { company: options.company } }),
        onchange: () => dialog?.set_value("task_name", ""),
      },
      {
        fieldname: "task_name", label: __("Task"), fieldtype: "Link", options: "Task",
        depends_on: (values) => inProject(values) && !!values.project_name,
        get_query: () => ({ filters: { project: dialog.get_value("project_name") } }),
      },
      {
        fieldname: "customer_name", label: __("Customer"), fieldtype: "Link",
        options: "HD Customer",
        depends_on: (values) => !!values.work_context && values.work_context !== "Internal",
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
      { fieldname: "from_time", label: __("Start Date and Time"), fieldtype: "Datetime", reqd: 1 },
      { fieldtype: "Column Break" },
      { fieldname: "duration_minutes", label: __("Duration (minutes)"), fieldtype: "Data", reqd: 1 },
      { fieldtype: "Section Break" },
      { fieldname: "description", label: __("Description"), fieldtype: "Small Text", reqd: 1 },
    ];
    if (booking) {
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
        const payload = bookingPayload(values, ticketArea, options);
        if (!payload) return;
        const button = dialog.get_primary_btn();
        if (button.prop("disabled")) return;
        button.prop("disabled", true);
        try {
          const result = await post(api + "book_technician_time", payload);
          dialog.hide();
          frappe.show_alert({
            message: __("Draft booking {0} saved.", [result.timesheet]),
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
    if (booking) {
      dialog.set_primary_action(
        replacing ? __("Replace Booking") : __("Save Correction"),
        correctionRequest(
          dialog, booking, replacing ? "replace_submitted_booking" : "correct_draft_booking",
          (values) => bookingPayload(values, ticketArea, options), afterSave,
        ),
      );
    }
    dialog.$wrapper.one("hidden.bs.modal", () => dialog.$wrapper.remove());
    dialog.show();

    if (booking) {
      // A Project change clears Task, so restore their saved values in order.
      const button = dialog.get_primary_btn();
      button.prop("disabled", true);
      const fill = async () => {
        for (const field of fields) {
          const key = field.fieldname;
          if (key === "activity_type" && historicalActivity) continue;
          if (key === "emergency" && booking.emergency != null) {
            await dialog.set_value(key, booking.emergency ? "Yes" : "No");
          } else if (key && booking[key] != null) {
            await dialog.set_value(key, booking[key]);
          }
        }
        dialog.refresh_dependency();
      };
      fill()
        .catch(() => showError(__("Some saved details could not be loaded. Check the fields before saving.")))
        .finally(() => button.prop("disabled", false));
    }
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
          if (booking.docstatus !== 2) {
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
      $("<button>", {
        id: "telectro-time-bookings",
        type: "button",
        class: "btn btn-default btn-sm mr-2 text-nowrap",
        text: __("Time Bookings"),
      }).on("click", () => openBookings(options)).insertAfter(toolbar);
    } catch {
      // Booking availability must not interrupt Desk startup.
    }
  }

  $(document).on("app_ready", installEntryPoint);
  $(installEntryPoint);
})();

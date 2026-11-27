(() => {
  const fields = ["customer", "service_area", "company", "employee", "activity_type",
    "project", "task", "ticket", "snapfix_reference"];
  const dependencies = ["from_date", "to_date", "company", "employee", "project"];
  const requests = new WeakMap();

  function scope(report, reportName) {
    const values = report.get_filter_values();
    return new URLSearchParams({
      report_name: reportName,
      ...Object.fromEntries(dependencies.map((name) => [name, values[name] || ""])),
    });
  }

  function configureControl(control) {
    // Frappe's default autocomplete renderer interprets option labels as HTML.
    control.awesomplete.item = function (item, input, index) {
      const option = document.createElement("li");
      option.id = "awesomplete_list_" + this.count + "_item_" + index;
      option.setAttribute("role", "option");
      option.setAttribute("aria-selected", "false");
      option.textContent = item.label;
      return option;
    };

    control.awesomplete.replace = (item) => control.$input.val(item.label);

    // Keep the selected label mapped to its ID while replacing dated suggestions.
    const readInput = control.get_input_value.bind(control);
    let selection;
    control.get_input_value = () => {
      const text = control.$input.val();
      selection = control.get_data().find(({ label }) => label === text)
        || (selection?.label === text ? selection : undefined);
      return selection ? selection.value : readInput();
    };
  }

  function setOptions(control, options) {
    const value = control.get_value();
    control.set_data(options);
    const selected = control.get_data().find((choice) => choice.value === value);
    if (selected) {
      control.$input.val(selected.label);
      control.get_value();
    }
  }

  function setup(report, reportName) {
    const controls = report.filters.filter(
      (control) => fields.includes(control.df.fieldname) && control.awesomplete
    );
    if (!controls.length) return;
    report.page.page_form.find(".telectro-booked-hours-filter-status").remove();
    const status = $("<div>", { class: "telectro-booked-hours-filter-status small text-muted w-100" })
      .appendTo(report.page.page_form);
    const message = $("<span>", { role: "status" }).appendTo(status);
    const retry = $("<button>", {
      type: "button", class: "btn btn-default btn-xs ml-2", text: __("Retry"),
    }).on("click", () => load()).appendTo(status);
    let state;
    let lastScope;
    let scopeTimer;

    function showState() {
      const active = controls.find((control) => control.$input.is(":focus"));
      const guidance = {
        loading: __("Loading filter choices…"),
        failed: __("Unable to load filter choices."),
        invalid: __("Select a valid reporting period to load filter choices."),
      };
      const empty = state === "ready" && active && !active.get_data().length;
      message.text(guidance[state] || (empty ? __("No authorized choices for this filter in the selected scope.") : ""));
      retry.toggle(state === "failed");
      status.toggle(Boolean(message.text()));
    }

    async function load() {
      const args = scope(report, reportName);
      const params = args.toString();
      lastScope = params;
      const request = new AbortController();
      requests.get(report)?.abort();
      requests.set(report, request);
      for (const control of controls) {
        setOptions(control, []);
        control.awesomplete.ul.replaceChildren();
      }
      const start = args.get("from_date"), end = args.get("to_date");
      if (!start || !end || start > end) {
        state = "invalid";
        showState();
        return;
      }

      const isCurrent = () => !request.signal.aborted && report === frappe.query_report
        && controls.every((control) => report.filters.includes(control))
        && scope(report, reportName).toString() === params;
      state = "loading";
      showState();
      try {
        const response = await fetch("/api/method/telephony.api.booking_report_filters.get_options?" + params, {
          headers: { Accept: "application/json" },
          signal: request.signal,
        });
        if (!response.ok) throw new Error();
        const { message: choices } = await response.json();
        if (!isCurrent()) return;
        for (const control of controls) setOptions(control, choices[control.df.fieldname]);
        state = "ready";
      } catch {
        if (!isCurrent()) return;
        state = "failed";
      }
      showState();
    }

    function scopeChanged() {
      clearTimeout(scopeTimer);
      scopeTimer = setTimeout(() => {
        if (controls.every((control) => report.filters.includes(control))
            && scope(report, reportName).toString() !== lastScope) load();
      }, 0);
    }

    for (const control of controls) {
      configureControl(control);
      control.$input.on("focus blur", () => queueMicrotask(showState));
    }
    for (const control of report.filters) {
      if (dependencies.includes(control.df.fieldname)) {
        control.$input?.on("change", scopeChanged);
        control.on_change = () => {
          scopeChanged();
          if (!report._no_refresh) report.refresh(true);
        };
      }
    }
    load();
  }

  frappe.telectro_booked_hours_filters = { setup };
})();

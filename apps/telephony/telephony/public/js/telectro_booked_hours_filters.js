(() => {
  const fields = ["customer", "service_area"];
  const requests = new WeakMap();

  function scope(report, reportName) {
    const values = report.get_filter_values();
    return {
      report_name: reportName,
      from_date: values.from_date || "",
      to_date: values.to_date || "",
      company: values.company || "",
      employee: values.employee || "",
    };
  }

  async function load(report, reportName) {
    const controls = fields.map((name) => report.get_filter(name));
    const args = scope(report, reportName);
    const params = new URLSearchParams(args).toString();
    // Immediately drop options from the previous period and roster.
    requests.get(report)?.abort();
    controls.forEach((control) => {
      control.set_data([]);
      control.awesomplete.ul.replaceChildren();
    });
    if (!args.from_date || !args.to_date || args.from_date > args.to_date) return;
    const request = new AbortController();
    requests.set(report, request);
    try {
      const response = await fetch("/api/method/telephony.api.booking_report_filters.get_options?" + params, {
        headers: { Accept: "application/json" },
        signal: request.signal,
      });
      if (!response.ok) return;
      const { message } = await response.json();
      if (request.signal.aborted || report !== frappe.query_report ||
          controls.some((control, i) => control !== report.get_filter(fields[i])) ||
          new URLSearchParams(scope(report, reportName)).toString() !== params) return;
      fields.forEach((name, i) => controls[i].set_data(message[name]));
    } catch {
      // Keep the native report and its existing exact-value filters usable.
    }
  }

  function setup(report, reportName) {
    if (fields.some((name) => !report.get_filter(name)?.awesomplete)) return;
    for (const name of fields) {
      const control = report.get_filter(name);
      // Frappe's default autocomplete renderer interprets option labels as HTML.
      control.awesomplete.item = function (item, input, index) {
        const option = document.createElement("li");
        option.id = "awesomplete_list_" + this.count + "_item_" + index;
        option.setAttribute("role", "option");
        option.setAttribute("aria-selected", "false");
        option.textContent = item.label;
        return option;
      };
    }
    for (const name of ["from_date", "to_date", "company", "employee"]) {
      const control = report.filters.find((filter) => filter.df.fieldname === name);
      if (control) {
        control.on_change = () => {
          if (report._no_refresh) return;
          load(report, reportName);
          report.refresh(true);
        };
      }
    }
    load(report, reportName);
  }

  frappe.telectro_booked_hours_filters = { setup };
})();

(() => {
  const route = "customer-labour-cost-analysis";
  const method = "/api/method/telephony.ftelephony.page.customer_labour_cost_analysis.customer_labour_cost_analysis.";
  const presets = [
    ["today", __("Today")], ["this_week", __("This Week")], ["last_week", __("Last Week")],
    ["this_month", __("This Month")], ["custom", __("Custom")],
  ];

  function element(tag, text, className) {
    const node = document.createElement(tag);
    if (text) node.textContent = text;
    if (className) node.className = className;
    return node;
  }

  frappe.pages[route].on_page_load = (wrapper) => {
    const page = frappe.ui.make_app_page({
      parent: wrapper, title: __("Customer Labour Cost Analysis"), single_column: true,
    });
    const root = element("section", null, "clc-export");
    page.main.get(0).append(root);
    const heading = element("header", null, "clc-heading");
    const scope = element("p", __("Uses recorded work within your Supervisor reporting grants."));
    heading.append(element("h2", __("Compare the labour cost of serving Customer accounts")), scope);
    const form = element("form", null, "clc-form");
    const select = element("select", null, "form-control");
    select.id = "clc-period-preset";
    for (const [value, label] of presets) {
      const option = element("option", label);
      option.value = value;
      select.append(option);
    }
    select.value = "this_month";
    const label = element("label", __("Reporting period"));
    label.htmlFor = select.id;
    const custom = element("div", null, "clc-dates");
    const date = (name, labelText) => {
      const label = element("label", labelText);
      const input = element("input", null, "form-control");
      input.type = "date";
      input.id = name;
      label.htmlFor = name;
      custom.append(label, input);
      return input;
    };
    const from = date("clc-from", __("From date"));
    const to = date("clc-to", __("To date"));
    const status = element("p", null, "clc-status");
    status.setAttribute("aria-live", "polite");
    const download = element("button", __("Download Excel workbook"), "btn btn-primary");
    download.type = "submit";
    const instructions = element("p", __("Open the workbook, enter hourly rates on Technician Rates, then enter revenue excluding VAT on Customer Financial Summary."), "clc-instructions");
    form.append(label, select, custom, status, download);
    root.append(heading, form, instructions);

    let current;
    let controller;
    async function refresh() {
      controller?.abort();
      const request = new AbortController();
      controller = request;
      current = null;
      download.disabled = true;
      custom.hidden = select.value !== "custom";
      const params = new URLSearchParams({preset: select.value});
      if (!custom.hidden) {
        if (!from.value || !to.value || from.value > to.value) {
          status.textContent = __("Choose a valid start and end date.");
          return;
        }
        params.set("from_date", from.value);
        params.set("to_date", to.value);
      }
      status.textContent = __("Checking reporting period…");
      try {
        const response = await fetch(method + "get_period?" + params, {signal: request.signal, cache: "no-store"});
        if (!response.ok) throw new Error(response.status);
        const {message} = await response.json();
        if (request.signal.aborted) return;
        if (custom.hidden) {
          from.value = message.from_date;
          to.value = message.to_date;
        }
        if (message.dev_test) {
          scope.textContent = __("Controlled DEV test scope · 20–26 November 2026.");
          if (select.value === "this_month") {
            select.value = "custom";
            custom.hidden = false;
            params.set("preset", "custom");
            params.set("from_date", message.from_date);
            params.set("to_date", message.to_date);
          }
        }
        status.textContent = __("Site dates {0} to {1}, inclusive.", [message.from_date, message.to_date]);
        current = params;
        download.disabled = false;
      } catch (error) {
        if (!request.signal.aborted) status.textContent = error.message === "403" ?
          __("This workbook is unavailable for your reporting access.") :
          __("Check the dates and try a reporting period of 93 days or fewer.");
      }
    }

    form.addEventListener("change", refresh);
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!current || download.disabled) return;
      const selection = current;
      const period = status.textContent;
      download.disabled = true;
      status.textContent = __("Preparing Excel workbook…");
      try {
        const response = await fetch(method + "download_workbook?" + selection, {cache: "no-store"});
        if (response.status === 403) {
          if (current === selection) {
            current = null;
            status.textContent = __("This workbook is unavailable for your reporting access.");
          }
          return;
        }
        if (!response.ok) throw new Error();
        const url = URL.createObjectURL(await response.blob());
        const link = element("a");
        link.href = url;
        link.download = response.headers.get("Content-Disposition")?.match(/filename="?([^";]+)/i)?.[1] ||
          "Customer Labour Cost Analysis.xlsx";
        link.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
        if (current === selection) status.textContent = period;
      } catch {
        if (current === selection) status.textContent = __("Unable to download the workbook. Check your reporting access and try again.");
      } finally {
        if (current === selection) download.disabled = false;
      }
    });
    wrapper.refreshCustomerLabourPeriod = refresh;
  };

  frappe.pages[route].on_page_show = (wrapper) => wrapper.refreshCustomerLabourPeriod();
})();

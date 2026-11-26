(() => {
  const name = "technician-work-overview";
  const overviewMethod = "telephony.ftelephony.page.technician_work_overview.technician_work_overview.get_overview";
  const dimensions = [
    ["technician", __("Technicians")], ["customer", __("Customers")],
    ["service_area", __("Service Areas")], ["work_context", __("Work Contexts")],
    ["project", __("Projects")], ["activity_type", __("Activities")], ["reference", __("Work References")],
  ];
  const presets = [
    ["today", __("Today")], ["this_week", __("This Week")], ["last_week", __("Last Week")],
    ["this_month", __("This Month")], ["custom", __("Custom")],
  ];
  const colors = new Map([
    ["Helpdesk", "helpdesk"], ["Project", "project"], ["Customer Support", "support"], ["Internal", "internal"],
  ]);

  const contextOrder = new Map([...colors.keys()].map((context, index) => [context, index]));

  function element(tag, className, value) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (value !== undefined && value !== null) node.textContent = value;
    return node;
  }

  function button(label, handler, className = "two-button") {
    const node = element("button", className, label);
    node.type = "button";
    node.addEventListener("click", handler);
    return node;
  }

  function duration(microseconds) {
    if (!microseconds) return __("0 min");
    const minutes = Math.round(microseconds / 60000000);
    if (!minutes) return __("<1 min");
    const hours = Math.floor(minutes / 60);
    const remainder = minutes % 60;
    if (!hours) return __("{0} min", [minutes]);
    return remainder ? __("{0} h {1} min", [hours, remainder]) : __("{0} h", [hours]);
  }

  function displayDate(value) {
    const day = new Date(value.slice(0, 10) + "T00:00:00Z");
    return new Intl.DateTimeFormat(undefined, {
      day: "numeric", month: "short", year: "numeric", timeZone: "UTC",
    }).format(day);
  }

  function dateRange(period) {
    return period.from_date === period.to_date ? displayDate(period.from_date) :
      displayDate(period.from_date) + " – " + displayDate(period.to_date);
  }

  function segments(contexts, className) {
    const bar = element("div", className);
    const ordered = contexts.filter(([, value]) => value > 0).sort(([left], [right]) =>
      (contextOrder.get(left) ?? contextOrder.size) - (contextOrder.get(right) ?? contextOrder.size));
    const composition = ordered.map(([name, amount]) => __(name) + " " + duration(amount)).join(" · ");
    if (composition && className === "two-group-bar") {
      bar.setAttribute("role", "img");
      bar.setAttribute("aria-label", composition);
      bar.title = composition;
    } else {
      bar.setAttribute("aria-hidden", "true");
    }
    for (const [name, amount] of ordered) {
      const segment = element("span", "two-color-" + (colors.get(name) || "internal"));
      segment.style.flexGrow = String(amount);
      bar.append(segment);
    }
    return bar;
  }

  function openReport(filters) {
    frappe.route_options = { ...filters };
    frappe.set_route("query-report", "Supervisor Booked Hours");
  }

  function workEntry(row, showTechnician) {
    const references = [
      row.ticket && __("Ticket {0}", [row.ticket]),
      row.project && [row.project_name, row.project].filter(Boolean).join(" · "),
      row.task && __("Task {0}", [row.task]),
      row.snapfix_reference && __("Snapfix {0}", [row.snapfix_reference]),
    ].filter(Boolean);
    if (row.reference_state === "Restricted reference" || row.reference_state === "Missing historical reference") {
      references.push(__(row.reference_state));
    }
    const card = element("details", "two-entry");
    const summary = element("summary", "two-entry-summary");
    const identity = element("div", "two-entry-identity");
    const title = row.customer || row.unlisted_customer || row.project_name ||
      (row.work_context === "Internal" ? __("Internal work") : __(row.customer_type));
    const label = element("strong", "two-entry-name", title);
    const date = displayDate(row.day);
    identity.append(label, element("span", "two-muted", showTechnician ? row.technician + " · " + date : date));
    const preview = [...references, row.service_area].filter(Boolean).join(" · ");
    if (preview) identity.append(element("span", "two-entry-preview two-muted", preview));
    const effort = element("div", "two-entry-effort");
    const context = element("span", "two-tag two-color-" + (colors.get(row.work_context) || "internal"), __(row.work_context));
    const time = element("strong", null, duration(row.booked_us));
    effort.append(context, time, element("span", "two-chevron"));
    summary.append(identity, effort);
    const info = element("div", "two-entry-info");
    const metadata = element("dl", "two-entry-meta");
    for (const [key, value] of [
      [__("Activity"), row.activity_type], [__("Service Area"), row.service_area],
      [__("Reference"), references.join(" · ")], [__("Status"), row.status],
    ]) {
      if (value) metadata.append(element("dt", null, key), element("dd", null, value));
    }
    const note = element("p", "two-description",
      row.description || (row.reference_state === "Restricted reference" ?
        __("Description unavailable for this reference.") : __("No description available.")));
    const times = element("div", "two-muted", row.from_time.slice(11, 16) + "–" + row.to_time.slice(11, 16));
    info.append(metadata, note, times);
    card.append(summary, info);
    return card;
  }

  frappe.pages[name].on_page_load = (wrapper) => {
    const page = frappe.ui.make_app_page({
      parent: wrapper, title: __("Technician Work Overview"), single_column: true,
    });
    const root = element("div", "two-dashboard");
    page.main.get(0).append(root);

    const toolbar = element("div", "two-toolbar");
    const presetBar = element("div", "two-presets");
    presetBar.setAttribute("aria-label", __("Reporting period"));
    const custom = element("form", "two-custom");
    const from = element("input", "form-control");
    const to = element("input", "form-control");
    from.type = to.type = "date";
    from.required = to.required = true;
    from.setAttribute("aria-label", __("From date"));
    to.setAttribute("aria-label", __("To date"));
    const apply = element("button", "two-button two-primary", __("Apply dates"));
    apply.type = "submit";
    custom.append(from, to, apply);
    const reportButton = button(__("Open Detailed Report"), () => {
      if (current) openReport(current.report_filters);
    }, "two-button two-primary");
    toolbar.append(presetBar, reportButton, custom);
    const status = element("div", "two-status");
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");
    const body = element("div", "two-sections");
    root.append(toolbar, status, body);

    let preset = "this_week";
    let dimension = "technician";
    let group = null;
    let offset = 0;
    let appliedDates = null;
    let lastPeriod = null;
    let current = null;
    let pending = null;

    const presetButtons = presets.map(([key, label]) => {
      const item = button(label, () => {
        preset = key;
        group = null;
        offset = 0;
        if (key === "custom" && !appliedDates && lastPeriod) {
          from.value = lastPeriod.from_date;
          to.value = lastPeriod.to_date;
          appliedDates = { from_date: from.value, to_date: to.value };
        }
        refresh();
      }, "two-segment");
      presetBar.append(item);
      return [key, item];
    });

    custom.addEventListener("submit", (event) => {
      event.preventDefault();
      appliedDates = { from_date: from.value, to_date: to.value };
      group = null;
      offset = 0;
      refresh();
    });

    function render(data) {
      const hero = element("section", "two-hero");
      const heroTitle = element("div", "two-hero-heading");
      heroTitle.append(element("h2", null, __("Recorded work for the full period")),
        element("span", "two-scope", __("Limited to your reporting grants")));
      const metrics = element("div", "two-metrics");
      for (const [label, value] of [
        [__("Total booked time"), duration(data.booked_us)],
        [__("Technicians with work"), data.technician_count],
        [__("Customers served"), data.customer_count],
      ]) {
        const metric = element("div", "two-metric");
        metric.append(element("span", null, label), element("strong", null, value));
        metrics.append(metric);
      }
      hero.append(heroTitle, element("p", "two-period", dateRange(data.period)), metrics);
      const distribution = element("section", "two-panel two-distribution");
      distribution.append(element("h2", null, __("Where did our time go?")),
        element("p", "two-section-note two-muted", __("Work distribution for the full authorized period.")));
      distribution.append(segments(data.contexts.map((row) => [row.name, row.booked_us]), "two-distribution-bar"));
      const legend = element("ul", "two-contexts");
      for (const row of data.contexts) {
        const item = element("li");
        item.append(element("span", "two-dot two-color-" + (colors.get(row.name) || "internal")),
          element("span", null, __(row.name)), element("strong", null, duration(row.booked_us)));
        legend.append(item);
      }
      distribution.append(legend);

      const explorer = element("section", "two-panel two-explorer");
      explorer.append(element("h2", null, __("Explore recorded work")));
      const tabs = element("div", "two-tabs");
      tabs.setAttribute("aria-label", __("Explore by"));
      for (const [key, label] of dimensions) {
        const tab = button(label, () => {
          dimension = key;
          group = null;
          offset = 0;
          refresh();
        }, "two-segment");
        tab.setAttribute("aria-pressed", String(key === dimension));
        tabs.append(tab);
      }
      explorer.append(tabs, element("p", "two-section-note two-muted",
        __("Select a group to filter individual work. Each thin bar shows that group’s work mix.")));
      const columns = element("div", "two-explore-columns");
      const list = element("div", "two-groups");
      if (!data.groups.length) {
        list.append(element("p", "two-empty", __("No recorded work for this view.")));
      }
      for (const item of data.groups) {
        const choice = button("", () => {
          group = item.key === group ? null : item.key;
          offset = 0;
          refresh();
        }, "two-group");
        choice.setAttribute("aria-pressed", String(item.key === group));
        const summary = element("div", "two-group-line");
        summary.append(element("strong", null, item.label), element("span", "two-duration", duration(item.booked_us)));
        choice.append(summary);
        if (item.secondary) choice.append(element("span", "two-muted", item.secondary));
        choice.append(segments(Object.entries(item.contexts), "two-group-bar"));
        list.append(choice);
      }
      const details = element("div", "two-details");
      const detailHeading = element("div", "two-detail-heading");
      detailHeading.append(element("h3", null, data.selected?.label || __("Individual work")),
        element("span", "two-muted", data.detail_count === 1 ? __("1 entry") : __("{0} entries", [data.detail_count])));
      if (data.selected) {
        detailHeading.append(button(__("Clear selection"), () => {
          group = null;
          offset = 0;
          refresh();
        }));
      }
      details.append(detailHeading);
      if (!data.detail.length) details.append(element("p", "two-empty", __("No authorized bookings in this selection.")));
      const showTechnician = dimension !== "technician" || !data.selected;
      for (const row of data.detail) details.append(workEntry(row, showTechnician));
      if (offset || data.next_offset !== null) {
        const paging = element("div", "two-paging");
        if (offset) paging.append(button(__("Previous"), () => {
          offset = data.previous_offset;
          refresh();
        }));
        if (data.next_offset !== null) paging.append(button(__("Next"), () => {
          offset = data.next_offset;
          refresh();
        }));
        details.append(paging);
      }
      columns.append(list, details);
      explorer.append(columns);
      body.replaceChildren(hero, distribution, explorer);
    }

    async function refresh() {
      pending?.abort();
      const request = new AbortController();
      pending = request;
      current = null;
      reportButton.disabled = true;
      body.replaceChildren();
      for (const [key, item] of presetButtons) item.setAttribute("aria-pressed", String(key === preset));
      custom.hidden = preset !== "custom";
      if (preset === "custom" && !appliedDates) {
        status.textContent = __("Choose a start and end date.");
        return;
      }
      if (preset === "custom" && appliedDates.from_date > appliedDates.to_date) {
        status.textContent = __("The start date must be on or before the end date.");
        return;
      }
      status.textContent = __("Loading recorded work…");
      root.setAttribute("aria-busy", "true");
      const params = new URLSearchParams({ preset, dimension, offset: String(offset) });
      if (preset === "custom") for (const [key, value] of Object.entries(appliedDates)) params.set(key, value);
      if (group) params.set("group", group);
      try {
        const response = await fetch("/api/method/" + overviewMethod + "?" + params, {
          signal: request.signal, headers: { Accept: "application/json" },
        });
        if (request.signal.aborted) return;
        if (!response.ok) {
          status.textContent = response.status === 403 ?
            __("This work view is unavailable for your reporting access.") :
            __("Unable to load recorded work. Check the date range and try again.");
          if (group) status.append(" ", button(__("Clear selection"), () => { group = null; offset = 0; refresh(); }));
          return;
        }
        const data = (await response.json()).message;
        if (request.signal.aborted) return;
        render(data);
        current = data;
        lastPeriod = data.period;
        reportButton.disabled = false;
        status.textContent = "";
      } catch {
        if (!request.signal.aborted) status.textContent = __("Unable to load recorded work. Try again.");
      } finally {
        if (!request.signal.aborted) root.removeAttribute("aria-busy");
      }
    }

    wrapper.refreshWorkOverview = refresh;
  };

  frappe.pages[name].on_page_show = (wrapper) => wrapper.refreshWorkOverview();
})();

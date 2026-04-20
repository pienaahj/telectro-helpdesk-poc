frappe.query_reports["Partner Archived Tickets"] = {
  filters: [],

  onload(report) {
    suppress_actions(report);
  },

  refresh(report) {
    suppress_actions(report);
  },

  formatter(value, row, column, data, default_formatter) {
    value = default_formatter(value, row, column, data);

    if (!data || !data.name) return value;

    if (column.fieldname === "name" || column.fieldname === "subject") {
      return `<a href="/app/partner-ticket/${encodeURIComponent(data.name)}">${value}</a>`;
    }

    return value;
  },
};

function suppress_actions(report) {
  const hide = () => {
    const wrapper = $(report.page.wrapper);

    wrapper
      .find('.actions-btn-group-label[data-label="Actions"]')
      .closest("button")
      .hide();

    wrapper
      .find("button.btn.btn-default.ellipsis")
      .filter((_, el) => (el.innerText || "").trim() === "Actions")
      .hide();

    wrapper
      .find("button.btn.btn-primary.btn-sm")
      .filter((_, el) => (el.innerText || "").includes("Actions"))
      .hide();

    wrapper
      .find('[data-label="Actions"]')
      .closest(".btn-group, .custom-actions, button")
      .hide();
  };

  setTimeout(hide, 0);
  setTimeout(hide, 100);
  setTimeout(hide, 300);
}

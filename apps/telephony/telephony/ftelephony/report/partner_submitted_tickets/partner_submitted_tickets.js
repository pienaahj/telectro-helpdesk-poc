frappe.query_reports["Partner Submitted Tickets"] = {
  filters: [],

  onload() {
    suppress_actions();
  },

  refresh() {
    suppress_actions();
  },

  formatter(value, row, column, data, default_formatter) {
    const formatted = default_formatter(value, row, column, data);

    if (!data || !data.name) return formatted;

    if (column.fieldname === "name" || column.fieldname === "subject") {
      const label = value || data[column.fieldname] || data.name;
      return `<a href="/app/partner-ticket/${encodeURIComponent(data.name)}">${frappe.utils.escape_html(String(label))}</a>`;
    }

    return formatted;
  },
};

function suppress_actions() {
  const hide = () => {
    $("button.btn.btn-primary.btn-sm")
      .filter((_, el) => (el.innerText || "").includes("Actions"))
      .hide();

    $("button.btn.btn-default.ellipsis")
      .filter((_, el) => (el.innerText || "").trim() === "Actions")
      .hide();

    $('.actions-btn-group-label[data-label="Actions"]')
      .closest("button")
      .hide();
  };

  setTimeout(hide, 0);
  setTimeout(hide, 100);
  setTimeout(hide, 300);
}

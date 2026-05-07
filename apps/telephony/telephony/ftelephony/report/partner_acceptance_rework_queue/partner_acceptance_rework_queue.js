frappe.query_reports["Partner Acceptance Rework Queue"] = {
  filters: [],

  formatter(value, row, column, data, default_formatter) {
    value = default_formatter(value, row, column, data);

    if (!data || !data.name) return value;

    if (column.fieldname === "name" || column.fieldname === "subject") {
      return `<a href="/app/hd-ticket/${encodeURIComponent(data.name)}">${value}</a>`;
    }

    return value;
  },
};

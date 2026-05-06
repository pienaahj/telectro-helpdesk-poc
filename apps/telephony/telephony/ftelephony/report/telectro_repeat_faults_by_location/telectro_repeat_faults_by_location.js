frappe.query_reports["TELECTRO Repeat Faults by Location"] = {
  filters: [
    {
      fieldname: "period",
      label: "Period",
      fieldtype: "Select",
      options: ["Last 7 days", "Last 14 days", "Last 30 days", "Custom"],
      default: "Last 14 days",
      reqd: 1,
      onchange() {
        const period = frappe.query_report.get_filter_value("period");
        const is_custom = period === "Custom";

        frappe.query_report.toggle_filter_display("from_date", !is_custom);
        frappe.query_report.toggle_filter_display("to_date", !is_custom);
      },
    },
    {
      fieldname: "from_date",
      label: "From Date",
      fieldtype: "Date",
      depends_on: "eval:doc.period == 'Custom'",
    },
    {
      fieldname: "to_date",
      label: "To Date",
      fieldtype: "Date",
      depends_on: "eval:doc.period == 'Custom'",
    },
    {
      fieldname: "customer",
      label: "Customer",
      fieldtype: "Link",
      options: "Customer",
    },
    {
      fieldname: "campus",
      label: "Campus",
      fieldtype: "Link",
      options: "Location",
    },
    {
      fieldname: "site",
      label: "Fault Point",
      fieldtype: "Link",
      options: "Location",
    },
    {
      fieldname: "service_area",
      label: "Service Area",
      fieldtype: "Data",
    },
    {
      fieldname: "fault_category",
      label: "Fault Category",
      fieldtype: "Data",
    },
    {
      fieldname: "severity",
      label: "Severity",
      fieldtype: "Select",
      options: "\nSev1\nSev2\nSev3\nSev4",
    },
    {
      fieldname: "minimum_repeat_count",
      label: "Minimum Repeat Count",
      fieldtype: "Int",
      default: 2,
      reqd: 1,
    },
  ],

  onload(report) {
    const period = frappe.query_report.get_filter_value("period");
    const is_custom = period === "Custom";

    frappe.query_report.toggle_filter_display("from_date", !is_custom);
    frappe.query_report.toggle_filter_display("to_date", !is_custom);
  },

  formatter(value, row, column, data, default_formatter) {
    value = default_formatter(value, row, column, data);

    if (!data) return value;

    if (column.fieldname === "latest_ticket" && data.latest_ticket) {
      return `<a href="/app/hd-ticket/${encodeURIComponent(data.latest_ticket)}">${value}</a>`;
    }

    return value;
  },
};

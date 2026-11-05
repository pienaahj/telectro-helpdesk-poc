frappe.query_reports["Data Request Escalation Report"] = {
  filters: [],

  formatter(value, row, column, data, default_formatter) {
    const formatted = default_formatter(
      value,
      row,
      column,
      data
    );

    if (!data || !column) {
      return formatted;
    }

    if (
      column.fieldname !== "currently_overdue" &&
      column.fieldname !== "escalation_captured"
    ) {
      return formatted;
    }

    const state = String(value || "").trim();

    if (state !== "YES" && state !== "NO") {
      return formatted;
    }

    const isOverdue = column.fieldname === "currently_overdue";

    let background;
    let foreground;

    if (isOverdue && state === "YES") {
      background = "#fee2e2";
      foreground = "#991b1b";
    } else if (!isOverdue && state === "YES") {
      background = "#dbeafe";
      foreground = "#1e40af";
    } else {
      background = "#f3f4f6";
      foreground = "#4b5563";
    }

    return `
      <span style="
        display: inline-block;
        padding: 2px 9px;
        border-radius: 999px;
        background: ${background};
        color: ${foreground};
        font-weight: 600;
        white-space: nowrap;
      ">${state}</span>
    `;
  }
};

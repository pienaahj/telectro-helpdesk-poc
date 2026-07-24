frappe.query_reports["TELECTRO Unclaimed War Room"] = {
  formatter(value, row, column, data, default_formatter) {
    const formatted = default_formatter(
      value,
      row,
      column,
      data
    );

    if (!data) {
      return formatted;
    }

    const idle = Number(data.idle_minutes || 0);

    if (column.fieldname === "ticket") {
      const indicator =
        idle >= 240
          ? "🔴 "
          : idle >= 60
            ? "🟠 "
            : "🟢 ";

      return `${indicator}${formatted}`;
    }

    if (column.fieldname === "idle_minutes") {
      let background;
      let foreground;

      if (idle >= 240) {
        background = "#fee2e2";
        foreground = "#991b1b";
      } else if (idle >= 60) {
        background = "#fef3c7";
        foreground = "#92400e";
      } else {
        background = "#dcfce7";
        foreground = "#166534";
      }

      return `
        <span style="
          display: inline-block;
          padding: 2px 8px;
          border-radius: 999px;
          background: ${background};
          color: ${foreground};
          font-weight: 600;
          line-height: 1.6;
        ">
          ${formatted}
        </span>
      `;
    }

    return formatted;
  },
};

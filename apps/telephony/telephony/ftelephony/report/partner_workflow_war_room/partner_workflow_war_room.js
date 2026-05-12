frappe.query_reports["Partner Workflow War Room"] = {
  filters: [],

  onload(report) {
    suppress_actions(report);
    inject_note_cell_css(report);
  },

  refresh(report) {
    suppress_actions(report);
    inject_note_cell_css(report);
  },

  formatter(value, row, column, data, default_formatter) {
    if (column.fieldname === "latest_partner_note") {
      const text = String(value || "").trim();

      if (!text) {
        return "";
      }

      const preview = text;
      const escapedPreview = frappe.utils.escape_html(preview);
      const escapedFullText = frappe.utils.escape_html(text);

      const message = JSON.stringify(`
        <div style="white-space: pre-wrap; line-height: 1.5;">
          <div>${escapedFullText}</div>
        </div>
      `);

      return `
        <div class="partner-war-room-note-preview" title="${escapedFullText}">
          <span>${escapedPreview}</span>
          <a
            href="#"
            class="ml-2"
            onclick='frappe.msgprint({title: "Latest Partner Note", message: ${message}, wide: true}); return false;'
          >View full</a>
        </div>
      `;
    }

    value = default_formatter(value, row, column, data);

    if (!data || !data.name) {
      return value;
    }

    if (column.fieldname === "name" || column.fieldname === "subject") {
      return `<a href="/app/hd-ticket/${encodeURIComponent(data.name)}">${value}</a>`;
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

function inject_note_cell_css(report) {
  const wrapper = $(report.page.wrapper);

  if (wrapper.find("#partner-war-room-note-report-css").length) {
    return;
  }

  wrapper.append(`
    <style id="partner-war-room-note-report-css">
      .partner-war-room-note-preview {
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        max-width: 500px;
      }

      .partner-war-room-note-preview a {
        white-space: nowrap !important;
      }
    </style>
  `);
}

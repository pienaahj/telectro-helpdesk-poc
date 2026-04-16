frappe.query_reports["Partner Active Tickets"] = {
  filters: [],

  onload(report) {
    suppress_actions(report);
  },

  refresh(report) {
    suppress_actions(report);
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

(() => {
  const PARTNER_ROLES = [
    "TELECTRO-POC Role - Partner",
    "TELECTRO-POC Role - Partner Creator",
  ];

  const INTERNAL_BYPASS_ROLES = [
    "System Manager",
    "Pilot Admin",
    "TELECTRO-POC Role - Supervisor Governance",
    "TELECTRO-POC Role - Coordinator Ops",
  ];

  const BLOCKED_PREFIXES = [
    "/app/report",
    "/app/workspace",
    "/app/contact",
    "/app/email-account",
    "/app/user",
    "/app/role",
  ];

  const TARGET_ROUTE = "/app/telectro-poc-partner";
  let guardStarted = false;

  function hideElement(el) {
    el.classList.add("hide");
    el.style.setProperty("display", "none", "important");
    el.setAttribute("aria-hidden", "true");
  }

  function redirectAway() {
    const currentPath = window.location.pathname || "";
    if (currentPath === TARGET_ROUTE) return;

    if (window.frappe && typeof frappe.set_route === "function") {
      frappe.show_alert?.({
        message: __("This area is not available for Partner users."),
        indicator: "orange",
      });

      frappe.set_route("telectro-poc-partner");
      return;
    }

    window.location.href = TARGET_ROUTE;
  }

  function getRoles() {
    if (!window.frappe) return [];
    if (Array.isArray(frappe.user_roles)) return frappe.user_roles;
    if (frappe.boot && Array.isArray(frappe.boot.user?.roles)) {
      return frappe.boot.user.roles;
    }
    if (frappe.boot && Array.isArray(frappe.boot.user_roles)) {
      return frappe.boot.user_roles;
    }
    return [];
  }

  function getCurrentUser() {
    if (!window.frappe) return "";
    return (
      frappe.session?.user ||
      frappe.boot?.user?.name ||
      frappe.boot?.user_info?.name ||
      ""
    );
  }

  function isInternalBypassUser() {
    const user = getCurrentUser();
    const roles = getRoles();

    if (user === "Administrator") return true;
    return INTERNAL_BYPASS_ROLES.some((role) => roles.includes(role));
  }

  function isPartnerUser() {
    if (isInternalBypassUser()) return false;

    const roles = getRoles();
    return PARTNER_ROLES.some((role) => roles.includes(role));
  }

  function isBlockedPath(pathname) {
    return BLOCKED_PREFIXES.some((prefix) => pathname.startsWith(prefix));
  }

  function isPartnerWorkspaceRoute() {
    const path = window.location.pathname || "";
    const hash = window.location.hash || "";
    const route = window.frappe?.router?.current_route || [];
    const routeText = Array.isArray(route)
      ? route.join("/")
      : String(route || "");

    return (
      path === "/app/telectro-poc-partner" ||
      path === "/app/telectro-poc-partner-workspace" ||
      path.includes("telectro-poc-partner") ||
      hash.includes("telectro-poc-partner") ||
      routeText.includes("telectro-poc-partner")
    );
  }

  function normaliseText(value) {
    return (value || "").replace(/\s+/g, " ").trim();
  }

  function hideUnsafePartnerWorkspaceActions() {
    if (!isPartnerWorkspaceRoute()) return;
    if (!isPartnerUser()) return;

    const directSelectors = [
      ".btn-new-workspace",
      ".btn-edit-workspace",
      ".duplicate-page",
      ".page-actions .primary-action",
      ".standard-actions .primary-action",
      ".page-head .btn-primary",
    ];

    for (const selector of directSelectors) {
      for (const el of document.querySelectorAll(selector)) {
        const text = normaliseText(el.textContent);
        const title = normaliseText(el.getAttribute("title"));
        const aria = normaliseText(el.getAttribute("aria-label"));
        const dataLabel = normaliseText(el.getAttribute("data-label"));

        const isUnsafeWorkspaceAction =
          selector === ".btn-new-workspace" ||
          selector === ".btn-edit-workspace" ||
          selector === ".duplicate-page" ||
          text === "+ New" ||
          text === "New" ||
          text === "Edit" ||
          text === "Duplicate" ||
          title === "New" ||
          title === "Edit Workspace" ||
          title === "Duplicate Workspace" ||
          aria === "New" ||
          aria === "Edit Workspace" ||
          aria === "Duplicate Workspace" ||
          dataLabel === "New" ||
          dataLabel === "+ New";

        if (isUnsafeWorkspaceAction) {
          hideElement(el);
        }
      }
    }

    for (const el of document.querySelectorAll(
      "button, a, .dropdown-item, [role='button']",
    )) {
      const text = normaliseText(el.textContent);
      const title = normaliseText(el.getAttribute("title"));
      const aria = normaliseText(el.getAttribute("aria-label"));
      const dataLabel = normaliseText(el.getAttribute("data-label"));

      const isUnsafeWorkspaceAction =
        text === "+ New" ||
        text === "New" ||
        text === "Edit" ||
        text === "Duplicate" ||
        title === "New" ||
        title === "Edit Workspace" ||
        title === "Duplicate Workspace" ||
        aria === "New" ||
        aria === "Edit Workspace" ||
        aria === "Duplicate Workspace" ||
        dataLabel === "New" ||
        dataLabel === "+ New";

      if (isUnsafeWorkspaceAction) {
        hideElement(el);
      }
    }
  }

  function redirectAway() {
    const currentPath = window.location.pathname || "";
    if (currentPath === TARGET_ROUTE) return;

    if (window.frappe && typeof frappe.set_route === "function") {
      frappe.show_alert?.({
        message: __("This area is not available for Partner users."),
        indicator: "orange",
      });

      frappe.set_route("telectro-poc-partner");
      return;
    }

    window.location.href = TARGET_ROUTE;
  }

  function guardRoute() {
    const path = window.location.pathname || "";

    if (!isPartnerUser()) return;
    if (!isBlockedPath(path)) return;

    redirectAway();
  }

  function waitForBootAndStart() {
    const roles = getRoles();

    if (!roles.length) {
      window.setTimeout(waitForBootAndStart, 300);
      return;
    }

    if (guardStarted) return;
    guardStarted = true;

    guardRoute();
    hideUnsafePartnerWorkspaceActions();

    let lastPath = window.location.pathname;
    window.setInterval(() => {
      const currentPath = window.location.pathname;
      if (currentPath !== lastPath) {
        lastPath = currentPath;
        guardRoute();
      }

      hideUnsafePartnerWorkspaceActions();
    }, 300);

    const observer = new MutationObserver(() => {
      hideUnsafePartnerWorkspaceActions();
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", waitForBootAndStart);
  } else {
    waitForBootAndStart();
  }
})();

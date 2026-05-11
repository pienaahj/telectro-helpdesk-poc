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

  function hidePartnerWorkspaceNewButton() {
    const path = window.location.pathname || "";
    const isPartnerWorkspace =
      path === "/app/telectro-poc-partner" ||
      path === "/app/telectro-poc-partner-workspace";

    if (!isPartnerWorkspace) return;
    if (!isPartnerUser()) return;

    const directSelectors = [
      ".btn-new-workspace",
      ".btn-edit-workspace",
      ".duplicate-page",
    ];

    for (const selector of directSelectors) {
      for (const el of document.querySelectorAll(selector)) {
        hideElement(el);
      }
    }

    const controls = Array.from(
      document.querySelectorAll("button, a, .dropdown-item"),
    );

    for (const el of controls) {
      const text = (el.textContent || "").trim();
      const title = (el.getAttribute("title") || "").trim();
      const aria = (el.getAttribute("aria-label") || "").trim();

      const isUnsafeWorkspaceAction =
        text === "+ New" ||
        text === "New" ||
        text === "Edit" ||
        title === "Duplicate Workspace" ||
        title === "Edit Workspace" ||
        aria === "Duplicate Workspace" ||
        aria === "Edit Workspace";

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
    hidePartnerWorkspaceNewButton();

    let lastPath = window.location.pathname;
    window.setInterval(() => {
      const currentPath = window.location.pathname;
      if (currentPath !== lastPath) {
        lastPath = currentPath;
        guardRoute();
      }

      hidePartnerWorkspaceNewButton();
    }, 300);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", waitForBootAndStart);
  } else {
    waitForBootAndStart();
  }
})();

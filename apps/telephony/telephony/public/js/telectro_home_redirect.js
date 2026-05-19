(() => {
  let redirectStarted = false;
  let lastPath = "";

  function getDeskRoute(path) {
    return path.replace(/^\/app\//, "");
  }

  function getRoles() {
    if (!window.frappe) return [];

    if (Array.isArray(frappe.user_roles)) {
      return frappe.user_roles;
    }

    if (frappe.boot && Array.isArray(frappe.boot.user?.roles)) {
      return frappe.boot.user.roles;
    }

    if (frappe.boot && Array.isArray(frappe.boot.user_roles)) {
      return frappe.boot.user_roles;
    }

    return [];
  }

  function hasRole(roles, role) {
    return Array.isArray(roles) && roles.includes(role);
  }

  function getTargetPath(roles) {
    const isSupervisor = hasRole(
      roles,
      "TELECTRO-POC Role - Supervisor Governance",
    );
    const isCoordinator = hasRole(roles, "TELECTRO-POC Role - Coordinator Ops");
    const isTech = hasRole(roles, "TELECTRO-POC Role - Tech");
    const isPartner =
      hasRole(roles, "TELECTRO-POC Role - Partner") ||
      hasRole(roles, "TELECTRO-POC Role - Partner Creator");

    if (isSupervisor) return "/app/telectro-poc-ops";
    if (isCoordinator) return "/app/telectro-poc-coordinator";
    if (isTech) return "/app/telectro-poc-tech";
    if (isPartner) return "/app/telectro-poc-partner";

    return "";
  }

  function shouldNormalize(path) {
    if (!path) return false;

    return [
      "/app",
      "/app/",
      "/app/home",
      "/app/helpdesk",
      "/app/workspace",
      "/app/workspace/",
      "/app/telectro-poc-tech",
      "/app/telectro-poc-coordinator",
      "/app/telectro-poc-ops",
      "/app/telectro-poc-partner",
    ].includes(path);
  }

  function normalizeLandingRoute() {
    const roles = getRoles();
    if (!roles.length) return;

    const path = window.location.pathname || "";
    const target = getTargetPath(roles);

    if (!target) return;
    if (!shouldNormalize(path)) return;
    if (path === target) return;

    if (window.frappe && typeof frappe.set_route === "function") {
      frappe.set_route(getDeskRoute(target));
      return;
    }

    window.location.replace(target);
  }

  function waitForBootAndStart() {
    const roles = getRoles();

    if (!roles.length) {
      window.setTimeout(waitForBootAndStart, 300);
      return;
    }

    if (redirectStarted) return;
    redirectStarted = true;

    normalizeLandingRoute();

    lastPath = window.location.pathname || "";

    window.setInterval(() => {
      const currentPath = window.location.pathname || "";

      if (currentPath !== lastPath) {
        lastPath = currentPath;
        normalizeLandingRoute();
      }
    }, 300);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", waitForBootAndStart);
  } else {
    waitForBootAndStart();
  }
})();

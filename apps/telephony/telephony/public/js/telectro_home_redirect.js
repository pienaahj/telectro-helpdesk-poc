(() => {
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

    if (isSupervisor) return "/app/telectro-poc-ops";
    if (isCoordinator) return "/app/telectro-poc-coordinator";
    if (isTech) return "/app/telectro-poc-tech";
    return "/app";
  }

  function shouldNormalize(path) {
    if (!path) return false;

    // Only normalize true landing / stale remembered workspace routes.
    // Do NOT redirect away from intentional routes like query reports,
    // lists, documents, etc.
    return [
      "/app",
      "/app/",
      "/app/helpdesk",
      "/app/telectro-poc-tech",
      "/app/telectro-poc-coordinator",
      "/app/telectro-poc-ops",
    ].includes(path);
  }

  function run() {
    if (!window.frappe || !frappe.boot || !frappe.boot.user) return;

    const roles = frappe.boot.user.roles || [];
    const path = window.location.pathname || "";
    const target = getTargetPath(roles);

    if (!target) return;
    if (!shouldNormalize(path)) return;
    if (path === target) return;

    window.location.replace(target);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }
})();

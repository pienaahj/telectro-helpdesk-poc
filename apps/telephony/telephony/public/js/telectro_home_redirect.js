(() => {
  let redirectStarted = false;
  let lastPath = "";

  const ROUTES = {
    tech: "/app/telectro-poc-tech",
    coordinator: "/app/telectro-poc-coordinator",
    ops: "/app/telectro-poc-ops",
    partner: "/app/telectro-poc-partner",
  };

  const GENERIC_LANDING_PATHS = new Set([
    "/app",
    "/app/",
    "/app/home",
    "/app/helpdesk",
    "/app/workspace",
    "/app/workspace/",
  ]);

  const TELECTRO_WORKSPACE_PATHS = new Set(Object.values(ROUTES));

  function getDeskRoute(path) {
    return path.replace(/^\/app\/?/, "");
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

  function getRoleFlags(roles) {
    const isSystemManager = hasRole(roles, "System Manager");
    const isSupervisor = hasRole(
      roles,
      "TELECTRO-POC Role - Supervisor Governance",
    );
    const isCoordinator = hasRole(roles, "TELECTRO-POC Role - Coordinator Ops");
    const isTech = hasRole(roles, "TELECTRO-POC Role - Tech");
    const isPartner =
      hasRole(roles, "TELECTRO-POC Role - Partner") ||
      hasRole(roles, "TELECTRO-POC Role - Partner Creator");

    return {
      isSystemManager,
      isSupervisor,
      isCoordinator,
      isTech,
      isPartner,
      isPrivilegedInternal: isSystemManager || isSupervisor,
    };
  }

  function getTargetPath(roles) {
    const flags = getRoleFlags(roles);

    if (flags.isSupervisor) return ROUTES.ops;
    if (flags.isCoordinator) return ROUTES.coordinator;
    if (flags.isTech) return ROUTES.tech;
    if (flags.isPartner) return ROUTES.partner;

    return "";
  }

  function isUsersOwnWorkspace(path, roles) {
    const flags = getRoleFlags(roles);

    if (path === ROUTES.ops) {
      return flags.isSupervisor;
    }

    if (path === ROUTES.coordinator) {
      return flags.isCoordinator;
    }

    if (path === ROUTES.tech) {
      return flags.isTech || flags.isCoordinator || flags.isSupervisor;
    }

    if (path === ROUTES.partner) {
      return flags.isPartner;
    }

    return false;
  }

  function canStayOnExplicitTelectroWorkspace(path, roles, isInitialCheck) {
    const flags = getRoleFlags(roles);

    if (!TELECTRO_WORKSPACE_PATHS.has(path)) {
      return true;
    }

    // On initial boot/login, never trust a stale workspace route inherited from
    // the previous browser user. Send the user to their own landing workspace.
    if (isInitialCheck) {
      return isUsersOwnWorkspace(path, roles);
    }

    // After boot, allow System Manager / Supervisor Governance users to inspect
    // explicit POC workspaces for maintenance.
    if (flags.isPrivilegedInternal) {
      return true;
    }

    return isUsersOwnWorkspace(path, roles);
  }

  function shouldNormalize(path, roles, isInitialCheck) {
    if (!path) return false;

    if (GENERIC_LANDING_PATHS.has(path)) {
      return true;
    }

    if (
      TELECTRO_WORKSPACE_PATHS.has(path) &&
      !canStayOnExplicitTelectroWorkspace(path, roles, isInitialCheck)
    ) {
      return true;
    }

    return false;
  }

  function normalizeLandingRoute(isInitialCheck = false) {
    const roles = getRoles();
    if (!roles.length) return;

    const path = window.location.pathname || "";
    const target = getTargetPath(roles);

    if (!target) return;
    if (!shouldNormalize(path, roles, isInitialCheck)) return;
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

    normalizeLandingRoute(true);

    lastPath = window.location.pathname || "";

    window.setInterval(() => {
      const currentPath = window.location.pathname || "";

      if (currentPath !== lastPath) {
        lastPath = currentPath;
        normalizeLandingRoute(false);
      }
    }, 300);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", waitForBootAndStart);
  } else {
    waitForBootAndStart();
  }
})();

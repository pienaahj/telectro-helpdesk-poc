(() => {
	const CUSTOMER_PORTAL_HOME = "/helpdesk/my-tickets";
	const WRAPPED_MARKER = "__telectro_customer_login_landing__";

	function install_customer_login_landing_guard() {
		const native_handler = window.login?.login_handlers?.[200];

		if (typeof native_handler !== "function") {
			return;
		}

		if (native_handler[WRAPPED_MARKER]) {
			return;
		}

		const wrapped_handler = function (data) {
			const home_page = frappe.utils.sanitise_redirect(
				data?.home_page
			);

			if (
				data?.message === "No App"
				&& home_page === CUSTOMER_PORTAL_HOME
			) {
				try {
					window.localStorage?.removeItem("last_visited");
				} catch {
					// Storage may be unavailable in restricted browser modes.
				}

				window.location.href = home_page;
				return;
			}

			return native_handler.apply(this, arguments);
		};

		wrapped_handler[WRAPPED_MARKER] = true;

		window.login.login_handlers[200] = wrapped_handler;
	}

	$(document).on(
		"login_rendered",
		install_customer_login_landing_guard
	);
})();

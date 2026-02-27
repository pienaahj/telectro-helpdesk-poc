(() => {
  if (!window.frappe?.datetime?.convert_to_user_tz) return;
  if (window.__telectro_datetime_guard_installed) return;
  window.__telectro_datetime_guard_installed = true;

  const orig = frappe.datetime.convert_to_user_tz.bind(frappe.datetime);

  frappe.datetime.convert_to_user_tz = function (val, ...rest) {
    if (
      val === undefined ||
      val === null ||
      val === "" ||
      val === "undefined" ||
      val === "null"
    ) {
      return val;
    }
    return orig(val, ...rest);
  };
})();

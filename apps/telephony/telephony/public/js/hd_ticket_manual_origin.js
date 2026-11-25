/* Route only the first native Desk Save of a Ticket opened from the list's New action. */
(() => {
  if (!frappe.boot?.telectro_manual_ticket_create) return;

  const newTickets = new WeakSet();
  const nativeNewDoc = frappe.new_doc;
  const nativeCall = frappe.call;

  frappe.new_doc = function (doctype, options, initialize) {
    const route = frappe.get_route();
    if (doctype !== "HD Ticket" || route[0] !== "List" || route[1] !== doctype) {
      return nativeNewDoc.apply(this, arguments);
    }
    return nativeNewDoc.call(this, doctype, options, function (doc) {
      newTickets.add(doc);
      return initialize?.call(this, doc);
    });
  };

  frappe.call = function (options) {
    const doc = options?.args?.doc;
    if (
      options?.method === "frappe.desk.form.save.savedocs" &&
      options.args.action === "Save" &&
      doc?.__islocal &&
      newTickets.has(doc)
    ) {
      return nativeCall.call(this, {
        ...options,
        type: "POST",
        method: "telephony.hd_ticket_manual_origin.create",
      });
    }
    return nativeCall.apply(this, arguments);
  };
})();

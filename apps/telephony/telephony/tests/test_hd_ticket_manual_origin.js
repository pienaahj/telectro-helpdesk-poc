"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "../public/js/hd_ticket_manual_origin.js"), "utf8");
const savedocs = "frappe.desk.form.save.savedocs";
const dedicated = "telephony.hd_ticket_manual_origin.create";

let route = ["List", "HD Ticket", "List"];
const calls = [];
const frappe = {
  boot: {},
  get_route: () => route,
  new_doc(doctype, options, initialize) {
    const doc = { doctype, ...options, __islocal: 1 };
    initialize?.(doc);
    return doc;
  },
  call(options) {
    calls.push(options);
    return options;
  },
};

const nativeNew = frappe.new_doc;
const nativeCall = frappe.call;
vm.runInNewContext(source, { frappe });
assert.equal(frappe.new_doc, nativeNew);
assert.equal(frappe.call, nativeCall);

frappe.boot.telectro_manual_ticket_create = true;
vm.runInNewContext(source, { frappe });
let initialDoc;
const fresh = frappe.new_doc("HD Ticket", { custom_service_area: "PABX" }, (doc) => {
  initialDoc = doc;
});
assert.equal(fresh, initialDoc);
assert.equal(fresh.custom_service_area, "PABX");

function save(doc, action = "Save") {
  const callback = () => {};
  const response = frappe.call({ method: savedocs, args: { doc, action }, callback, freeze: true });
  assert.equal(response.args.doc, doc);
  assert.equal(response.callback, callback);
  assert.equal(response.freeze, true);
  return response;
}
assert.equal(save(fresh).method, dedicated);
assert.equal(calls.at(-1).type, "POST");
assert.equal(save({ ...fresh }).method, savedocs, "a duplicated document has a different identity");
assert.equal(save(fresh, "Cancel").method, savedocs);
fresh.__islocal = 0;
assert.equal(save(fresh).method, savedocs, "an ordinary edit uses native Save");
assert.equal(save(frappe.new_doc("Issue")).method, savedocs);
route = ["Form", "HD Ticket", "17"];
assert.equal(save(frappe.new_doc("HD Ticket")).method, savedocs);
assert.equal(frappe.call({ method: "frappe.client.insert", args: { doc: fresh } }).method,
  "frappe.client.insert");
console.log("PASS: scoped Desk new/save, duplicate, other entry points, and missing-schema boot.");

"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const source = fs.readFileSync(
  "apps/telephony/telephony/public/js/customer_resolution_action.js",
  "utf8"
);

const calls = [];
const dialogs = [];
const messages = [];
const buttons = {};

let response = ["emerald.portal.test@example.com"];
let lookupFails = false;

const frappe = {
  user_roles: ["System Manager"],
  ui: {
    form: { on() {} },
    Dialog: class {
      constructor(config) {
        this.config = config;
        dialogs.push(this);
      }
      show() {
        this.shown = true;
      }
    },
  },
  async call(args) {
    calls.push(args);
    if (lookupFails) {
      throw new Error("Lookup unavailable");
    }
    return { message: response };
  },
  msgprint(message) {
    messages.push(message);
  },
};

const context = vm.createContext({
  frappe,
  __: (value) => value,
  setTimeout() {},
});

vm.runInContext(
  source + `
    globalThis.pickerTestAPI = {
      customer_recipient_dialog_fields,
      add_customer_update_action,
      add_customer_resolution_action
    };
  `,
  context
);

const api = context.pickerTestAPI;

const frm = {
  doc: {
    name: "948",
    status: "Open",
    customer: "Emerald Life",
    raised_by: "hendrik@local.test",
    custom_request_source: "Telectro",
    via_customer_portal: 0,
  },
  custom_buttons: {},
  add_custom_button(label, callback) {
    buttons[label] = callback;
  },
};

async function run() {
  const fields = await api.customer_recipient_dialog_fields(frm);

  assert.equal(fields.length, 1);
  assert.equal(fields[0].fieldtype, "Select");
  assert.equal(fields[0].reqd, 1);
  assert.equal(
    fields[0].options,
    "\nemerald.portal.test@example.com"
  );

  assert.equal(
    calls[0].method,
    "telephony.customer_ticket_resolution.get_customer_recipient_options"
  );
  assert.equal(calls[0].args.ticket_name, "948");

  console.log("PICKER_VALID_OPTIONS=PASS");

  api.add_customer_update_action(frm);
  api.add_customer_resolution_action(frm);

  assert.equal(typeof buttons["Add Customer Update"], "function");
  assert.equal(typeof buttons["Resolve Customer Ticket"], "function");

  await buttons["Add Customer Update"]();
  await buttons["Resolve Customer Ticket"]();

  assert.equal(dialogs.length, 2);

  for (const dialog of dialogs) {
    assert.equal(dialog.shown, true);

    const recipient = dialog.config.fields.find(
      (field) => field.fieldname === "customer_recipient"
    );

    assert.ok(recipient);
    assert.equal(recipient.fieldtype, "Select");
    assert.equal(
      recipient.options,
      "\nemerald.portal.test@example.com"
    );
  }

  console.log("BOTH_CUSTOMER_DIALOGS=PASS");

  const portalFrm = {
    doc: {
      ...frm.doc,
      via_customer_portal: 1,
      custom_request_source: "Customer",
    },
  };

  const callsBefore = calls.length;
  const portalFields =
    await api.customer_recipient_dialog_fields(portalFrm);

  assert.equal(portalFields.length, 0);
  assert.equal(calls.length, callsBefore);

  console.log("PORTAL_REQUESTER_NO_LOOKUP=PASS");

  response = [];
  const emptyFields =
    await api.customer_recipient_dialog_fields(frm);

  assert.equal(emptyFields, null);
  assert.ok(messages.length > 0);

  console.log("EMPTY_OPTIONS_FAIL_CLOSED=PASS");

  response = "invalid";
  const invalidFields =
    await api.customer_recipient_dialog_fields(frm);

  assert.equal(invalidFields, null);

  console.log("INVALID_RESPONSE_FAIL_CLOSED=PASS");

  lookupFails = true;
  const failedFields =
    await api.customer_recipient_dialog_fields(frm);

  assert.equal(failedFields, null);

  console.log("LOOKUP_ERROR_FAIL_CLOSED=PASS");

  console.log("B4_12I_FRONTEND_PICKER_REGRESSIONS=PASS");
}

run().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

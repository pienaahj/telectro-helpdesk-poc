const assert = require("node:assert/strict");
const { execFileSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const appRoot = path.resolve(__dirname, "../..");
const approvedActivities = JSON.parse(execFileSync("python3", [
  "-c",
  "import json; from telephony.time_booking_activity_types import BOOKING_ACTIVITY_TYPES; print(json.dumps(BOOKING_ACTIVITY_TYPES))",
], { cwd: appRoot, encoding: "utf8" }));
const source = fs.readFileSync(
  path.join(appRoot, "telephony/public/js/telectro_time_booking.js"), "utf8",
);

function loadBookingForm() {
  const dialogs = [];
  class Dialog {
    constructor(config) {
      this.config = config;
      this.values = {};
      this.fields_dict = { duration_minutes: { $input: { attr() {} } } };
      this.$wrapper = { one() {} };
      this.button = { prop() {} };
      dialogs.push(this);
    }
    show() {}
    get_primary_btn() { return this.button; }
    set_primary_action() {}
    async set_value(key, value) { this.values[key] = value; }
    refresh_dependency() {}
  }
  const document = {};
  const context = {
    document,
    $: () => ({ on() {} }),
    frappe: {
      ui: { Dialog },
      datetime: {
        system_datetime: () => "2026-11-20 12:00:00",
        now_datetime(asDate) {
          assert.equal(asDate, true);
          return new Date(2026, 10, 20, 12);
        },
      },
      utils: { escape_html: (text) => text },
      msgprint: (message) => assert.fail(message.message),
    },
    __: (text, values = []) =>
      text.replace(/\{(\d+)\}/g, (_, index) => values[index]),
    moment: () => ({ isValid: () => true }),
  };
  const testSource = source.replace(
    /\}\)\(\);\s*$/,
    "globalThis.bookingForm = { openForm, bookingPayload };})();",
  );
  vm.runInNewContext(testSource, context);
  const { openForm, bookingPayload } = context.bookingForm;
  const options = {
    company: "Company A",
    activity_types: approvedActivities,
    service_areas: ["Routing"],
    work_locations: ["Remote"],
    work_origins: ["Direct / Ad-hoc"],
  };
  return {
    open(booking = null) {
      openForm(options, booking, () => {});
      return dialogs.at(-1);
    },
    payload(activity) {
      return bookingPayload({
        work_context: "Internal",
        activity_type: activity,
        work_location: "Remote",
        from_time: "2026-11-20 09:00:00",
        duration_minutes: "30",
        description: "Test work",
        work_origin: "Direct / Ad-hoc",
        emergency: "No",
      }, null, options);
    },
  };
}

function field(dialog, name) {
  return dialog.config.fields.find((item) => item.fieldname === name);
}

test("Start Date and Time opens on a valid date and starts blank and required", () => {
  const dialog = loadBookingForm().open();
  const start = field(dialog, "from_time");
  assert.equal(start.fieldtype, "Datetime");
  assert.equal(start.reqd, 1);
  assert.equal(start.default, undefined);
  assert.equal(dialog.values.from_time, undefined);
  assert.ok(start.options.startDate instanceof Date);
  assert.ok(Number.isFinite(start.options.startDate.getTime()));
});

test("Activity Type selector exposes the ordered catalog and starts blank", () => {
  const dialog = loadBookingForm().open();
  const activity = field(dialog, "activity_type");
  assert.equal(activity.fieldtype, "Select");
  assert.equal(activity.reqd, 1);
  assert.equal(activity.default, undefined);
  assert.deepEqual(Array.from(activity.options), ["", ...approvedActivities]);
  assert.deepEqual(Array.from(field(dialog, "work_context").options),
    ["", "Helpdesk", "Project", "Customer Support", "Internal"]);
});

test("Travel hides Work Location and omits even a previously selected location", () => {
  const form = loadBookingForm();
  const dialog = form.open();
  assert.ok(field(dialog, "activity_type").options.includes("Travel"));
  const location = field(dialog, "work_location");
  assert.equal(location.depends_on({ activity_type: "Travel" }), false);
  assert.equal(location.mandatory_depends_on({ activity_type: "Travel" }), false);
  const payload = form.payload("Travel");
  assert.equal(payload.activity_type, "Travel");
  assert.equal(Object.hasOwn(payload, "work_location"), false);
});

test("An approved non-Travel activity requires and includes Work Location", () => {
  const form = loadBookingForm();
  const activity = approvedActivities.find((value) => value !== "Travel");
  const location = field(form.open(), "work_location");
  assert.equal(location.depends_on({ activity_type: activity }), true);
  assert.equal(location.mandatory_depends_on({ activity_type: activity }), true);
  assert.equal(form.payload(activity).work_location, "Remote");
});

test("Historical classifications appear as guidance without becoming choices", async () => {
  const form = loadBookingForm();
  const draft = form.open({ docstatus: 0, activity_type: "Execution" });
  const replacement = form.open({ docstatus: 1, activity_type: "Execution" });
  const approved = form.open({ docstatus: 0, activity_type: approvedActivities[0] });
  await new Promise(setImmediate);

  for (const dialog of [draft, replacement]) {
    const activity = field(dialog, "activity_type");
    assert.match(activity.description, /Previous Activity Type: Execution/);
    assert.equal(activity.options.includes("Execution"), false);
    assert.equal(dialog.values.activity_type, undefined);
  }
  assert.equal(approved.values.activity_type, approvedActivities[0]);
});

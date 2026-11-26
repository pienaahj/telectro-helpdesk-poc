const assert = require("node:assert/strict");
const { webcrypto } = require("node:crypto");
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

function loadBookingForm(lookup = async () => [], response = null) {
  const requests = [];
  const submissions = [];
  const dialogs = [];
  class Dialog {
    constructor(config) {
      this.config = config;
      this.values = {};
      this.fields_dict = Object.fromEntries(config.fields.filter((df) => df.fieldname).map((df) => [
        df.fieldname, { df, $input: { attr() {}, val() {} }, set_options() {} },
      ]));
      this.$wrapper = { one() {} };
      this.button = { prop() {} };
      dialogs.push(this);
    }
    show() {}
    hide() {}
    get_primary_btn() { return this.button; }
    set_primary_action(label, action) { this.action = action; }
    get_value(key) { return this.values[key]; }
    async set_value(key, value) {
      if (value === this.values[key]) return;
      this.values[key] = value;
      await this.fields_dict[key]?.df.onchange?.();
    }
    refresh_dependency() {}
  }
  const document = {};
  const context = {
    document,
    crypto: webcrypto,
    $: () => ({ on() {} }),
    async fetch(url, options) {
      submissions.push({ url, body: JSON.parse(options.body) });
      return response || { ok: true, json: async () => ({ message: { timesheet: "TS-1" } }) };
    },
    frappe: {
      show_alert() {},
      ui: { Dialog },
      async call(request) {
        requests.push(request);
        const method = request.method.split(".").at(-1);
        const result = await lookup(method, request.args);
        return { message: method === "get_booking_reference_customer" && Array.isArray(result)
          ? { customer_name: null } : result };
      },
      datetime: {
        system_datetime: () => "2026-11-20 12:00:00",
        now_datetime(asDate) {
          assert.equal(asDate, true);
          return new Date(2026, 10, 20, 12);
        },
      },
      utils: { escape_html: (text) => text.replace(/&/g, "&amp;").replace(/</g, "&lt;") },
      msgprint: (message) => assert.fail(message.message),
    },
    __: (text, values = []) =>
      text.replace(/\{(\d+)\}/g, (_, index) => values[index]),
    moment: Object.assign(() => ({ isValid: () => true }), {
      utc(value) {
        let instant = new Date(value.replace(" ", "T") + "Z");
        return {
          isValid: () => Number.isFinite(instant.getTime()),
          add(minutes) { instant = new Date(instant.getTime() + minutes * 60_000); return this; },
          format: () => instant.toISOString().slice(0, 19).replace("T", " "),
        };
      },
    }),
  };
  const testSource = source.replace(
    /\}\)\(\);\s*$/,
    "globalThis.bookingForm = { openForm, openSavedWork, bookingPayload, preCreationText, post };})();",
  );
  vm.runInNewContext(testSource, context);
  const { openForm, openSavedWork, bookingPayload, preCreationText, post } = context.bookingForm;
  const options = {
    company: "Company A",
    activity_types: approvedActivities,
    service_areas: ["Routing"],
    work_locations: ["Remote"],
    work_origins: ["Direct / Ad-hoc"],
  };
  return {
    requests,
    submissions,
    preCreationText,
    post,
    openSaved(booking) {
      openSavedWork(booking, () => {});
      return dialogs.at(-1);
    },
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

test("The Helpdesk Ticket Link uses the booking-specific native search adapter", () => {
  const dialog = loadBookingForm().open();
  assert.equal(field(dialog, "ticket_name").get_query().query,
    "telephony.api.time_booking.search_booking_tickets");
});

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

const project = { id: "P-1", label: "<Pilot>" };
const otherProject = { id: "P-2", label: "Other Project" };
const task = { id: "T-1", label: "Pilot Task" };
const workStart = "2026-11-20 09:00:00";

async function setProjectInterval(dialog) {
  await dialog.set_value("work_context", "Project");
  await dialog.set_value("from_time", workStart);
  await dialog.set_value("duration_minutes", "30");
}

const optionIds = (dialog, fieldname) =>
  Array.from(field(dialog, fieldname).options, (option) => option.value || option);

test("Linked Customer follows the reference and clears stale selection", async () => {
  const form = loadBookingForm(async (method, args) => {
    if (method === "get_booking_ticket_area") return { service_area: "Routing" };
    if (method === "get_booking_projects") return [project, otherProject];
    if (method === "get_booking_tasks") return [];
    if (args.ticket_name === "973" || args.project_name === project.id) {
      return { customer_name: "Boschendal" };
    }
    return { customer_name: null };
  });
  const dialog = form.open();
  await dialog.set_value("work_context", "Helpdesk");
  await dialog.set_value("ticket_name", "973");
  assert.equal(dialog.values.derived_customer, "Boschendal");
  assert.equal(field(dialog, "customer_name").depends_on(dialog.values), false);
  await dialog.set_value("ticket_name", "972");
  assert.equal(field(dialog, "customer_name").depends_on(dialog.values), true);
  await dialog.set_value("customer_name", "Selected Customer");
  await dialog.set_value("ticket_name", "973");
  assert.equal(dialog.values.customer_name, "");
  await setProjectInterval(dialog);
  await dialog.set_value("project_name", project.id);
  assert.equal(dialog.values.derived_customer, "Boschendal");
  await dialog.set_value("project_name", otherProject.id);
  assert.equal(dialog.values.customer_name, "");
  assert.equal(dialog.values.derived_customer, "No Customer recorded.");
});

test("Scoped Projects load only for completed work and preserve required validation", async () => {
  const form = loadBookingForm(async () => [project]);
  const dialog = form.open();
  assert.equal(field(dialog, "project_name").fieldtype, "Select");
  assert.equal(field(dialog, "task_name").fieldtype, "Select");
  assert.equal(field(dialog, "project_name").mandatory_depends_on({ work_context: "Project" }), true);

  await dialog.set_value("work_context", "Project");
  await dialog.set_value("duration_minutes", "30");
  await dialog.set_value("from_time", "2026-11-20 11:59:00");
  assert.equal(form.requests.length, 0);
  await dialog.set_value("from_time", workStart);
  assert.equal(form.requests.at(-1).method, "telephony.api.time_booking.get_booking_projects");
  assert.equal(form.requests.at(-1).args.from_time, workStart);
  assert.equal(form.requests.at(-1).args.duration_minutes, 30);
  assert.deepEqual(optionIds(dialog, "project_name"), ["", project.id]);
  assert.equal(field(dialog, "project_name").options[1].label, "&lt;Pilot> (P-1)");
});

test("Changing Project, duration, or start clears dependent selections", async () => {
  const form = loadBookingForm(async (method, args) => {
    if (method === "get_booking_projects") return [project, otherProject];
    if (method === "get_booking_reference_customer") return { customer_name: null };
    assert.ok([project.id, otherProject.id].includes(args.project_name));
    return args.project_name === project.id ? [task] : [];
  });
  const dialog = form.open();
  await setProjectInterval(dialog);
  await dialog.set_value("project_name", project.id);
  await dialog.set_value("task_name", task.id);
  await dialog.set_value("project_name", otherProject.id);
  assert.equal(dialog.values.task_name, "");
  assert.deepEqual(optionIds(dialog, "task_name"), [""]);
  assert.equal(form.requests.at(-1).args.project_name, otherProject.id);

  await dialog.set_value("project_name", project.id);
  await dialog.set_value("task_name", task.id);
  await dialog.set_value("duration_minutes", "45");
  assert.equal(dialog.values.project_name, "");
  assert.equal(dialog.values.task_name, "");
  assert.equal(form.requests.at(-1).args.duration_minutes, 45);

  await dialog.set_value("project_name", project.id);
  await dialog.set_value("task_name", task.id);
  await dialog.set_value("from_time", "2026-11-19 08:45:00");
  assert.equal(dialog.values.project_name, "");
  assert.equal(dialog.values.task_name, "");
  assert.equal(form.requests.at(-1).args.from_time, "2026-11-19 08:45:00");
});

test("A stale Task response from the previous Project is discarded", async () => {
  let finishOld;
  const oldLookup = new Promise((resolve) => { finishOld = resolve; });
  const form = loadBookingForm(async (method, args) => {
    if (method === "get_booking_projects") return [project, otherProject];
    if (method === "get_booking_reference_customer") return { customer_name: null };
    return args.project_name === project.id ? oldLookup : [];
  });
  const dialog = form.open();
  await setProjectInterval(dialog);
  const pending = dialog.set_value("project_name", project.id);
  await new Promise(setImmediate);
  await dialog.set_value("project_name", otherProject.id);
  finishOld([task]);
  await pending;
  assert.equal(dialog.values.project_name, otherProject.id);
  assert.deepEqual(optionIds(dialog, "task_name"), [""]);
});

test("Corrections restore Projects and Tasks through exact scoped lookup after the interval", async () => {
  const form = loadBookingForm(async (method, args) => {
    assert.equal(args.from_time, workStart);
    assert.equal(args.duration_minutes, 30);
    return method === "get_booking_projects" ? [project] : [task];
  });
  const dialog = form.open({
    docstatus: 1, work_context: "Project", from_time: workStart, duration_minutes: 30,
    project_name: project.id, task_name: task.id,
  });
  await new Promise(setImmediate);
  assert.equal(dialog.values.project_name, project.id);
  assert.equal(dialog.values.task_name, task.id);
  assert.equal(form.requests[0].args.name, project.id);
  assert.equal(form.requests[1].args.name, task.id);
  assert.equal(form.requests[1].args.project_name, project.id);
});

test("Non-Project intervals never call the scoped lookup endpoints", async () => {
  const form = loadBookingForm();
  const dialog = form.open();
  for (const workContext of ["Helpdesk", "Customer Support", "Internal"]) {
    await dialog.set_value("work_context", workContext);
    await dialog.set_value("from_time", workStart);
    await dialog.set_value("duration_minutes", "30");
  }
  assert.equal(form.requests.length, 0);
  assert.equal(field(dialog, "ticket_name").options, "HD Ticket");
  assert.equal(field(dialog, "customer_name").options, "HD Customer");
});

test("Save sends scoped IDs only and rejects selections for a stale interval", async () => {
  const form = loadBookingForm(async (method) => method === "get_booking_projects" ? [project] : [task]);
  const dialog = form.open();
  await setProjectInterval(dialog);
  await dialog.set_value("project_search", "Pilot");
  await dialog.set_value("project_name", project.id);
  await dialog.set_value("task_name", task.id);
  const values = {
    ...dialog.values, description: "Pilot work", activity_type: "Repair & Maintenance",
    work_origin: "Direct / Ad-hoc", service_area: "Routing", work_location: "Remote", emergency: "No",
  };
  await assert.rejects(dialog.config.primary_action({ ...values, duration_minutes: "90" }), /Select an eligible Project/);
  assert.equal(form.submissions.length, 0);
  await dialog.config.primary_action(values);
  const { url, body } = form.submissions[0];
  assert.equal(url, "/api/method/telephony.api.time_booking.book_technician_time");
  assert.equal(body.project_name, project.id);
  assert.equal(body.task_name, task.id);
  assert.equal(Object.hasOwn(body, "project_search"), false);
  assert.equal(Object.hasOwn(body, "task_search"), false);
});

test("Pre-creation presentation distinguishes exact duration, confirmed zero and unknown", () => {
  const { preCreationText } = loadBookingForm();
  assert.match(preCreationText(1000001), /1\.000001 seconds, included/);
  assert.match(preCreationText(86400000000), /86400 seconds, included/);
  assert.match(preCreationText(0), /0 seconds, included/);
  for (const unknown of [null, undefined, -1, "0", 86400000001]) {
    assert.match(preCreationText(unknown), /not established/);
  }
});


test("Saved Helpdesk work posts only owned-booking inputs and preserves fractional seconds", async () => {
  const { openSaved, requests, submissions } = loadBookingForm();
  const dialog = openSaved({
    work_context: "Helpdesk", docstatus: 1, name: "TS-1", modified: "2026-11-20 12:00:00",
    description: "Original note", from_time: "2026-11-20 10:00:00.123456",
    duration_minutes: 20, ticket_name: "42", customer_name: "Saved Customer",
  });
  await dialog.action({ description: "Updated note", reason: "Correct wording" });
  await dialog.action({
    description: "Updated note", reason: "Correct duration", change_interval: 1,
    from_time: "2026-11-20 10:00:00.123456", duration_minutes: 25,
  });
  assert.deepEqual(requests, []);
  const [note, interval] = submissions;
  assert.ok(note.url.endsWith(".replace_submitted_booking"));
  assert.deepEqual(Object.keys(note.body).sort(),
    ["description", "event_id", "expected_modified", "reason", "saved_work", "timesheet_name"]);
  assert.equal(note.body.saved_work, true);
  assert.equal(interval.body.from_time, "2026-11-20 10:00:00.123456");
  assert.equal(interval.body.duration_minutes, 25);
});


test("Recognized booking errors show actionable feedback with escaped text", async () => {
  const { post } = loadBookingForm(undefined, {
    ok: false, status: 422,
    json: async () => ({ error: { code: "original_creation_exceeded", message: "Adjust the start <time>." } }),
  });
  await assert.rejects(post("correction", {}), { message: "Adjust the start &lt;time>." });
});

test("Unknown booking codes and server errors use the generic feedback", async () => {
  for (const [status, code] of [[422, "toString"], [500, "original_creation_exceeded"]]) {
    const { post } = loadBookingForm(undefined, {
      ok: false, status,
      json: async () => ({ error: { code, message: "Internal error" } }),
    });
    await assert.rejects(post("correction", {}), {
      message: "Unable to save the booking. Check the details and try again.",
    });
  }
});

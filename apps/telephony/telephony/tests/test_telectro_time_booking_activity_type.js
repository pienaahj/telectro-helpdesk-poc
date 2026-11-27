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
      this.fields_dict = Object.fromEntries(config.fields.filter((df) => df.fieldname).map((df) => {
        const control = {
          df,
          $input: {
            attr() { return this; },
            on() { return this; },
            val: () => this.values[df.fieldname],
          },
          $wrapper: {
            find() { return this; },
            addClass() { return this; },
            attr() { return this; },
            text(value) { control.text = value; },
          },
          set_options() {},
          refresh() {},
        };
        return [df.fieldname, control];
      }));
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
    URLSearchParams,
    $: () => ({ on() { return this; }, appendTo() {} }),
    async fetch(url, options) {
      if (!options.method) {
        const parsed = new URL(url, "http://localhost");
        const method = parsed.pathname.split(".").at(-1);
        const args = Object.fromEntries(parsed.searchParams);
        if (args.duration_minutes) args.duration_minutes = Number(args.duration_minutes);
        requests.push({ method: "telephony.api.time_booking." + method, args });
        const result = await lookup(method, args);
        return { ok: true, json: async () => ({
          message: method === "get_booking_reference_customer" && Array.isArray(result)
            ? { customer_name: null } : result,
        }) };
      }
      submissions.push({ url, body: JSON.parse(options.body) });
      return response || { ok: true, json: async () => ({ message: { timesheet: "TS-1" } }) };
    },
    frappe: {
      show_alert() {},
      ui: { Dialog },
      datetime: {
        system_datetime: () => "2026-11-20 12:00:00",
        get_user_date_fmt: () => "YYYY-MM-DD",
        get_user_time_fmt: () => "HH:mm:ss",
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
    moment: Object.assign((value) => ({
      isValid: () => /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}(:\d{2})?$/.test(value),
    }), {
      utc(value) {
        let instant = new Date(value.replace(" ", "T") + "Z");
        return {
          isValid: () => Number.isFinite(instant.getTime()),
          add(minutes) { instant = new Date(instant.getTime() + minutes * 60_000); return this; },
          seconds: () => instant.getUTCSeconds(),
          format(format) {
            const stamp = instant.toISOString();
            if (format === "YYYY-MM-DD") return stamp.slice(0, 10);
            if (format === "HH:mm") return stamp.slice(11, 16);
            if (format === "HH:mm:ss") return stamp.slice(11, 19);
            return stamp.slice(0, 19).replace("T", " ");
          },
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
  assert.deepEqual(optionIds(dialog, "work_context"), ["", "Helpdesk", "Project", "Customer Support", "Internal"]);
  assert.equal(field(dialog, "work_context").options[1].label, "Helpdesk Ticket");
  assert.equal(field(dialog, "customer_name").only_select, 1);
  assert.equal(field(dialog, "unlisted_customer_name").description,
    "Only complete this if the Customer is not listed above.");
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

test("Revised intervals retain authorized references and clear those no longer available", async () => {
  const form = loadBookingForm(async (method, args) => {
    if (method === "get_booking_projects") {
      return args.from_time.startsWith("2026-11-19") ? [otherProject] : [project, otherProject];
    }
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
  assert.equal(dialog.values.project_name, project.id);
  assert.equal(dialog.values.task_name, task.id);
  assert.equal(form.requests.at(-1).args.duration_minutes, 45);

  await dialog.set_value("project_name", project.id);
  await dialog.set_value("task_name", task.id);
  await dialog.set_value("from_time", "2026-11-19 08:45:00");
  assert.equal(dialog.values.project_name, "");
  assert.equal(dialog.values.task_name, "");
  assert.equal(form.requests.at(-1).args.from_time, "2026-11-19 08:45:00");
});

test("A stale Project reply cannot populate a newer interval", async () => {
  let finishOld;
  const oldLookup = new Promise(resolve => { finishOld = resolve; });
  const form = loadBookingForm(async (method, args) => {
    assert.equal(method, "get_booking_projects");
    return args.duration_minutes === 30 ? oldLookup : [otherProject];
  });
  const dialog = form.open();
  await dialog.set_value("work_context", "Project");
  await dialog.set_value("from_time", workStart);
  const pending = dialog.set_value("duration_minutes", "30");
  await new Promise(setImmediate);
  await dialog.set_value("duration_minutes", "45");
  finishOld([project]);
  await pending;
  assert.deepEqual(optionIds(dialog, "project_name"), ["", otherProject.id]);
  assert.equal(dialog.fields_dict.project_name.df.read_only, 0);
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
  const exact = form.requests.filter(({args}) => args.name);
  assert.equal(exact[0].args.name, project.id);
  assert.equal(exact[1].args.name, task.id);
  assert.equal(exact[1].args.project_name, project.id);
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
  await assert.rejects(dialog.config.primary_action({ ...values, duration_minutes: "90" }), /Select a Project and optional Task/);
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
  assert.match(preCreationText(86400000000), /24 hours, included/);
  assert.match(preCreationText(0), /0 seconds, included/);
  assert.match(preCreationText(1), /0\.000001 seconds, included/);
  assert.match(preCreationText(1000000), /1 second, included/);
  assert.match(preCreationText(61000000), /1 minute 1 second, included/);
  for (const unknown of [null, undefined, -1, "0", 86400000001]) {
    assert.match(preCreationText(unknown), /not established/);
  }
});


test("Time is presented before context and the preview handles exact minutes and midnight", async () => {
  const dialog = loadBookingForm().open();
  const names = dialog.config.fields.map(x => x.fieldname).filter(Boolean);
  assert.deepEqual(Array.from(names.slice(0, 4)), ["from_time", "duration_minutes", "time_preview", "work_context"]);
  const preview = () => dialog.fields_dict.time_preview.text;
  assert.equal(preview(), "");
  await dialog.set_value("from_time", "2026-11-19 23:30:00");
  for (const [minutes, label] of [[1, "1 minute"], [15, "15 minutes"], [60, "1 hour"],
    [61, "1 hour 1 minute"], [90, "1 hour 30 minutes"], [120, "2 hours"], [135, "2 hours 15 minutes"]]) {
    await dialog.set_value("duration_minutes", String(minutes));
    assert.ok(preview().startsWith(label + " · Ends at "), preview());
  }
  await dialog.set_value("duration_minutes", "90");
  assert.equal(preview(), "1 hour 30 minutes · Ends at 2026-11-20 01:00");
  await dialog.set_value("from_time", "bad");
  assert.equal(preview(), "1 hour 30 minutes");
  await dialog.set_value("duration_minutes", "1.5");
  assert.equal(preview(), "");
});

test("Project choices distinguish prerequisite, loading, empty and failure", async () => {
  let finish;
  let failed = false;
  const pending = new Promise(resolve => { finish = resolve; });
  const form = loadBookingForm(async () => {
    if (failed) throw Error("private server failure");
    return pending;
  });
  const dialog = form.open();
  const projectControl = dialog.fields_dict.project_name;
  await dialog.set_value("work_context", "Project");
  assert.match(projectControl.df.description, /Enter your start date/);
  assert.equal(projectControl.df.read_only, 1);
  await dialog.set_value("from_time", workStart);
  const loading = dialog.set_value("duration_minutes", "30");
  await new Promise(setImmediate);
  assert.match(projectControl.df.description, /Finding/);
  assert.equal(projectControl.df.read_only, 1);
  finish([]);
  await loading;
  assert.match(projectControl.df.description, /No Projects match/);
  assert.equal(projectControl.df.read_only, 1);
  failed = true;
  await dialog.set_value("project_search", "retry");
  assert.match(projectControl.df.description, /Unable to load Projects/);
  assert.doesNotMatch(projectControl.df.description, /private/);
});

test("Only Customer Support exposes Work Origin and conditional fields", async () => {
  const form = loadBookingForm();
  const dialog = form.open();
  const origin = field(dialog, "work_origin");
  const snapfix = field(dialog, "external_reference");
  const other = field(dialog, "other_origin_description");
  for (const work_context of ["Helpdesk", "Project", "Internal"]) {
    assert.equal(origin.mandatory_depends_on({ work_context }), false);
    assert.equal(snapfix.depends_on({ work_context, work_origin: "Snapfix" }), false);
    assert.equal(other.depends_on({ work_context, work_origin: "Other" }), false);
  }
  await dialog.set_value("work_context", "Customer Support");
  assert.equal(origin.mandatory_depends_on(dialog.values), true);
  await dialog.set_value("work_origin", "Snapfix");
  await dialog.set_value("external_reference", "SF-stale");
  assert.equal(snapfix.mandatory_depends_on(dialog.values), true);
  await dialog.set_value("work_context", "Internal");
  await dialog.set_value("work_context", "Customer Support");
  assert.equal(dialog.values.work_origin, "");
  assert.equal(dialog.values.external_reference, "");
  assert.equal(field(dialog, "emergency").reqd, 1);
});

test("New work omits hidden origin metadata and same-context corrections preserve it", async () => {
  const form = loadBookingForm();
  const values = {
    work_context: "Internal", activity_type: "Travel", from_time: workStart,
    duration_minutes: "30", description: "Corrected", reason: "Correction", emergency: "No",
    work_origin: "Snapfix", external_reference: "SF-stale", other_origin_description: "Stale",
  };
  const fresh = form.open();
  await fresh.config.primary_action(values);
  assert.equal(Object.hasOwn(form.submissions[0].body, "work_origin"), false);
  assert.equal(Object.hasOwn(form.submissions[0].body, "external_reference"), false);
  assert.equal(Object.hasOwn(form.submissions[0].body, "other_origin_description"), false);

  for (const saved of [
    { work_origin: "Snapfix", external_reference: "SF-original", other_origin_description: null },
    { work_origin: "Other", external_reference: null, other_origin_description: "Original details" },
    { work_origin: null, external_reference: null, other_origin_description: null },
  ]) {
    const correction = form.open({
      ...saved, work_context: "Internal", docstatus: 1, name: "TS-1", modified: workStart,
    });
    await correction.action(values);
    const { body } = form.submissions.at(-1);
    for (const name of Object.keys(saved)) assert.equal(body[name], saved[name]);
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

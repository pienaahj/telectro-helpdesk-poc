"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { createRequire } = require("node:module");

const benchRoot = path.resolve(__dirname, "../../../..");
const deskRoot = path.join(benchRoot, "apps/helpdesk/desk");

const requireDesk = createRequire(
  path.join(deskRoot, "package.json")
);

const realDayjs = requireDesk("dayjs");
const fixedNow = realDayjs("2026-11-04T12:00:00");

const componentPath = path.join(
  deskRoot,
  "src/components/ticket/TicketCustomerSidebar.vue"
);

const source = fs.readFileSync(componentPath, "utf8");

const match = source.match(
  /function resolutionData\(\) \{[\s\S]*?\n\}(?=\n\nconst ticketBasicInfo)/
);

assert.ok(match, "Actual resolutionData function not found");

function dayjs(value) {
  return realDayjs(value === undefined ? fixedNow : value);
}

const context = vm.createContext({
  ticket: { data: {} },
  dayjs,
  formatTime: (seconds) => `${seconds}s`,
});

vm.runInContext(
  `${match[0]}\nglobalThis.testResolution = resolutionData;`,
  context
);

console.log("ACTUAL_DEV_RESOLUTION_FUNCTION=PASS");

function check(name, data, expectedLabel, expectedColor) {
  context.ticket.data = data;

  const result = context.testResolution();

  assert.equal(result.label, expectedLabel, name);
  assert.equal(result.color, expectedColor, name);

  console.log(`${name}=PASS`);
}

const ticket57 = {
  status: "Resolved",
  resolution_date: "2026-10-30 10:12:09.433409",
  resolution_by: "2026-11-03 18:00:00",
};

check(
  "TICKET_57_RESOLVED_BEFORE_DEADLINE",
  ticket57,
  "Fulfilled",
  "green"
);

check(
  "MISLEADING_AGREEMENT_STATUS_IGNORED",
  {
    ...ticket57,
    agreement_status: "Failed",
  },
  "Fulfilled",
  "green"
);

check(
  "LATE_RESOLUTION",
  {
    resolution_date: "2026-11-03 18:00:01",
    resolution_by: "2026-11-03 18:00:00",
  },
  "Failed",
  "red"
);

check(
  "EXACT_DEADLINE",
  {
    resolution_date: "2026-11-03 18:00:00",
    resolution_by: "2026-11-03 18:00:00",
  },
  "Fulfilled",
  "green"
);

check(
  "UNRESOLVED_BEFORE_DEADLINE",
  {
    resolution_date: null,
    resolution_by: "2026-11-04 13:00:00",
  },
  "Due in 3600s",
  "orange"
);

check(
  "UNRESOLVED_AFTER_DEADLINE",
  {
    resolution_date: null,
    resolution_by: "2026-11-04 11:00:00",
  },
  "Overdue",
  "red"
);

check(
  "MISSING_DEADLINE",
  {
    resolution_date: null,
    resolution_by: null,
  },
  "Not available",
  "gray"
);

check(
  "INVALID_DEADLINE",
  {
    resolution_date: null,
    resolution_by: "invalid-date",
  },
  "Not available",
  "gray"
);

check(
  "INVALID_RESOLUTION_DATE",
  {
    resolution_date: "invalid-date",
    resolution_by: "2026-11-03 18:00:00",
  },
  "Not available",
  "gray"
);

console.log("SLA_BEHAVIOURAL_TEST_COUNT=9");
console.log("SLA_5_PERSISTENT_REGRESSIONS=PASS");

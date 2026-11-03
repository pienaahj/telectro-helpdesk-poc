
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { createRequire } = require("node:module");

const benchRoot = path.resolve(__dirname, "../../../..");

const deskRoot = path.join(
  benchRoot,
  "apps/helpdesk/desk"
);

const requireDesk = createRequire(
  path.join(deskRoot, "package.json")
);

const { parse } = requireDesk("@vue/compiler-sfc");
const babelParser = requireDesk("@babel/parser");
const esbuild = requireDesk("esbuild");

const componentPath = path.join(
  deskRoot,
  "src/pages/ticket/TicketCommunication.vue"
);

const source = fs.readFileSync(componentPath, "utf8");

const { descriptor, errors } = parse(source, {
  filename: componentPath,
});

assert.equal(errors.length, 0);
assert.ok(descriptor.scriptSetup);
assert.ok(descriptor.template);

assert.match(
  descriptor.template.content,
  /:key="a\.file_id \|\| a\.name"/
);

console.log("ATTACHMENT_KEY_COMPATIBILITY=PASS");

const script = descriptor.scriptSetup.content;

const ast = babelParser.parse(script, {
  sourceType: "module",
  plugins: ["typescript"],
});

const functions = ast.program.body.filter(
  (node) =>
    node.type === "FunctionDeclaration" &&
    node.id?.name === "attachmentUrl"
);

assert.equal(functions.length, 1);

const fn = functions[0];
const functionSource = script.slice(fn.start, fn.end);

const compiled = esbuild.transformSync(
  `${functionSource}
globalThis.testResolver = attachmentUrl;`,
  {
    loader: "ts",
    target: "es2020",
    format: "cjs",
  }
).code;

console.log("ACTUAL_ATTACHMENT_RESOLVER=PASS");

function resolve(ticketName, attachment) {
  const context = vm.createContext({
    props: { ticketName },
    encodeURIComponent,
  });

  vm.runInContext(compiled, context);

  return context.testResolver(attachment);
}

const endpoint =
  "/api/method/telephony.customer_ticket_resolution.download_customer_completion_evidence";

const customerUrl = (ticketName, fileId) =>
  `${endpoint}?ticket_name=${encodeURIComponent(ticketName)}` +
  `&file_id=${encodeURIComponent(fileId)}`;

const cases = [
  {
    name: "NATIVE_INTERNAL_DOWNLOAD",
    ticket: "54",
    attachment: {
      name: "FILE-123",
      file_url: "/private/files/report.xls",
      file_name: "report.xls",
    },
    expected: "/private/files/report.xls",
  },
  {
    name: "CUSTOMER_AUTHORIZED_DOWNLOAD",
    ticket: "54",
    attachment: {
      file_id: "FILE-123",
      file_name: "report.xls",
    },
    expected: customerUrl("54", "FILE-123"),
  },
  {
    name: "CUSTOMER_URL_ENCODING",
    ticket: "54 & A",
    attachment: {
      file_id: "FILE/123&?",
      file_name: "report.xls",
    },
    expected: customerUrl("54 & A", "FILE/123&?"),
  },
  {
    name: "CUSTOMER_ENDPOINT_PRECEDENCE",
    ticket: "54",
    attachment: {
      file_id: "FILE-123",
      file_url: "/private/files/should-not-be-used.xls",
      file_name: "report.xls",
    },
    expected: customerUrl("54", "FILE-123"),
  },
  {
    name: "MISSING_CUSTOMER_TICKET_BLOCKED",
    ticket: "",
    attachment: {
      file_id: "FILE-123",
      file_url: "/private/files/should-not-be-used.xls",
      file_name: "report.xls",
    },
    expected: undefined,
  },
  {
    name: "MISSING_ATTACHMENT_IDENTITY_BLOCKED",
    ticket: "54",
    attachment: {
      file_name: "report.xls",
    },
    expected: undefined,
  },
  {
    name: "NATIVE_DOWNLOAD_WITHOUT_TICKET_NAME",
    ticket: "",
    attachment: {
      name: "FILE-123",
      file_url: "/private/files/report.xls",
      file_name: "report.xls",
    },
    expected: "/private/files/report.xls",
  },
];

for (const item of cases) {
  assert.equal(
    resolve(item.ticket, item.attachment),
    item.expected,
    item.name
  );

  console.log(`${item.name}=PASS`);
}

console.log(`ATTACHMENT_REGRESSION_TEST_COUNT=${cases.length}`);
console.log("TICKET_COMMUNICATION_ATTACHMENT_REGRESSIONS=PASS");

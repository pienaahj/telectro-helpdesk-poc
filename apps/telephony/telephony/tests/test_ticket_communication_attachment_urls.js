
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
// Regression: TicketConversation must supply the ticket identifier
// required by TicketCommunication's customer attachment URL resolver.

const conversationPath = path.join(
  deskRoot,
  "src/pages/ticket/TicketConversation.vue"
);

const conversationSource = fs.readFileSync(
  conversationPath,
  "utf8"
);

const {
  descriptor: conversationDescriptor,
  errors: conversationErrors,
} = parse(conversationSource, {
  filename: conversationPath,
});

assert.equal(conversationErrors.length, 0);
assert.ok(conversationDescriptor.template);
assert.ok(conversationDescriptor.scriptSetup);

// The parent obtains its ticket through the existing injection.
assert.match(
  conversationDescriptor.scriptSetup.content,
  /const ticket\s*=\s*inject\(ITicket\)/
);

function verifyTicketCommunicationBinding(template) {
  const usages = [
    ...template.matchAll(
      /<TicketCommunication\b[\s\S]*?\/>/g
    ),
  ];

  assert.equal(usages.length, 1);

  const invocation = usages[0][0];

  assert.match(
    invocation,
    /:attachments\s*=\s*"c\.attachments"/
  );

  assert.match(
    invocation,
    /:ticket-name\s*=\s*"ticket\.data\.name"/
  );
}

// Positive test: the real component passes the required prop.
const conversationTemplate =
  conversationDescriptor.template.content;

verifyTicketCommunicationBinding(conversationTemplate);

console.log("TICKET_CONVERSATION_PROP_BINDING=PASS");

// Negative control: reproduce the exact omission found in
// production and prove that this regression detects it.
const withoutTicketName = conversationTemplate.replace(
  ':ticket-name="ticket.data.name"',
  ""
);

assert.notEqual(withoutTicketName, conversationTemplate);

assert.throws(
  () => verifyTicketCommunicationBinding(withoutTicketName),
  { code: "ERR_ASSERTION" }
);

console.log("MISSING_TICKET_PROP_NEGATIVE_CONTROL=PASS");

console.log("TICKET_COMMUNICATION_ATTACHMENT_REGRESSIONS=PASS");

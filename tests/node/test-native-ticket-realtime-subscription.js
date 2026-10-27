
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const filename = process.argv[2];

assert.ok(filename, "Patched handler filename is required");

const source = fs.readFileSync(filename, "utf8");

const TELELECTRO_ENDPOINT =
  "/api/method/telephony.realtime_ticket_authorization.require_ticket_realtime_access";

const FRAPPE_ENDPOINT =
  "/api/method/frappe.realtime.can_subscribe_doc";

function simulate({
  event = "doc_subscribe",
  doctype = "HD Ticket",
  ticket = "902",
  status = 200,
  message = true,
  bodyPresent = true,
  error = null,
}) {
  const listeners = new Map();
  const joined = [];
  const requests = [];

  const namespace = {
    adapter: { rooms: new Map() },
    sockets: new Map(),
    to: () => ({ emit: () => {} }),
  };

  const socket = {
    id: "test-socket",
    user: "test@boschendal.co.za",
    user_type: "Website User",
    connected: true,
    rooms: new Set(),
    nsp: namespace,

    emit() {},

    on(name, callback) {
      listeners.set(name, callback);
    },

    join(room) {
      joined.push(room);

      if (!namespace.adapter.rooms.has(room)) {
        namespace.adapter.rooms.set(room, new Set());
      }

      namespace.adapter.rooms.get(room).add(this.id);
      this.rooms.add(room);
    },
  };

  namespace.sockets.set(socket.id, socket);

  function frappeRequest(url, requestSocket) {
    const record = {
      url,
      socket: requestSocket,
      query: null,
    };

    requests.push(record);

    return {
      type() {
        return this;
      },

      query(params) {
        record.query = params;
        return this;
      },

      end(callback) {
        const response =
          status === null
            ? null
            : {
                status,
                body: bodyPresent ? { message } : null,
              };

        callback(error, response);
        return this;
      },
    };
  }

  async function authorizedTicketRoomMembers(ns, room, ticketName, channel) {
    assert.equal(ns, namespace);
    assert.equal(channel, "native_doc");
    assert.equal(room, `open_doc:HD Ticket/${ticketName}`);
    return [...(ns.adapter.rooms.get(room) || [])]
      .map(id => ns.sockets.get(id))
      .filter(sock => sock && sock.connected && sock.rooms.has(room));
  }

  const sandbox = {
    module: { exports: {} },
    require(name) {
      assert.equal(name, "../utils");

      return {
        frappe_request: frappeRequest,
        authorized_ticket_room_members: authorizedTicketRoomMembers,
      };
    },
    console: { log() {} },
  };

  vm.runInNewContext(source, sandbox, { filename });

  sandbox.module.exports(namespace, socket);

  assert.ok(listeners.has(event), `Missing ${event} listener`);

  listeners.get(event)(doctype, ticket);

  return { joined, requests, socket };
}

let checked = 0;

function check(
  name,
  options,
  expectedJoin,
  expectedEndpoint,
  expectedChannel = null
) {
  const result = simulate(options);

  const event = options.event || "doc_subscribe";
  const doctype = options.doctype || "HD Ticket";
  const ticket = options.ticket || "902";

  const room =
    event === "doc_open"
      ? `open_doc:${doctype}/${ticket}`
      : `doc:${doctype}/${ticket}`;

  assert.equal(
    result.joined.includes(room),
    expectedJoin,
    `${name}: room membership mismatch`
  );

  assert.equal(
    result.requests.length,
    1,
    `${name}: unexpected number of permission requests`
  );

  const request = result.requests[0];

  assert.equal(request.url, expectedEndpoint);
  assert.equal(request.socket, result.socket);

  if (expectedChannel) {
    assert.equal(request.query.ticket_name, ticket);
    assert.equal(request.query.channel, expectedChannel);
  } else {
    assert.equal(request.query.doctype, doctype);
    assert.equal(request.query.docname, ticket);
  }

  checked += 1;
  console.log(`PASS ${String(checked).padStart(2, "0")} ${name}`);
}

const native = (name, options, allowed) =>
  check(
    name,
    options,
    allowed,
    TELELECTRO_ENDPOINT,
    "native_doc"
  );

// Native HD Ticket subscriptions: strict fail-closed decisions.
native("HD Ticket explicit approval", {}, true);

native(
  "HD Ticket permission denied",
  { status: 403, message: false },
  false
);

native(
  "HD Ticket server error",
  { status: 500 },
  false
);

native(
  "HD Ticket returned false",
  { message: false },
  false
);

native(
  "HD Ticket returned string true",
  { message: "true" },
  false
);

native(
  "HD Ticket response body missing",
  { bodyPresent: false },
  false
);

native(
  "HD Ticket no HTTP response",
  { status: null },
  false
);

native(
  "HD Ticket transport error",
  { error: new Error("Connection failed") },
  false
);

// Other DocTypes must retain Frappe's original authorisation.
check(
  "Other DocType allowed by Frappe",
  { doctype: "ToDo" },
  true,
  FRAPPE_ENDPOINT
);

check(
  "Other DocType denied by Frappe",
  { doctype: "ToDo", status: 403 },
  false,
  FRAPPE_ENDPOINT
);

// HD Ticket doc_open must use the Telectro native_doc policy.
native(
  "HD Ticket doc_open uses Telectro native authorisation",
  { event: "doc_open" },
  true
);

native(
  "HD Ticket doc_open denied by Telectro native policy",
  { event: "doc_open", status: 403, message: false },
  false
);

// Other DocTypes must preserve Frappe's doc_open policy.
check(
  "Other DocType doc_open allowed by Frappe",
  { event: "doc_open", doctype: "ToDo" },
  true,
  FRAPPE_ENDPOINT
);

check(
  "Other DocType doc_open denied by Frappe",
  { event: "doc_open", doctype: "ToDo", status: 403 },
  false,
  FRAPPE_ENDPOINT
);

assert.equal(checked, 14);

console.log();
console.log(`REALTIME_NATIVE_HANDLER_DECISIONS=${checked}`);
console.log("C3_130_NATIVE_SOCKET_HANDLER_BEHAVIOUR=PASS");

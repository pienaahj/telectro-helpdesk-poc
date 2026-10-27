
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const filename = process.argv[2];
assert.ok(filename, "Patched native handler filename required");

const source = fs.readFileSync(filename, "utf8");

const AUTHORITY =
  "/api/method/telephony.realtime_ticket_authorization.require_ticket_realtime_access";

const paths = [
  {
    name: "doc_subscribe",
    start: "doc_subscribe",
    stop: "doc_unsubscribe",
    room: (ticket) => `doc:HD Ticket/${ticket}`,
  },
  {
    name: "doc_open",
    start: "doc_open",
    stop: "doc_close",
    room: (ticket) => `open_doc:HD Ticket/${ticket}`,
  },
];

function createHarness() {
  const listeners = new Map();
  const requests = [];
  const joins = [];
  const leaves = [];

  const namespace = {
    adapter: { rooms: new Map() },
    sockets: new Map(),
    to() {
      return { emit() {} };
    },
  };

  const socket = {
    id: "test-customer-socket",
    user: "test@boschendal.co.za",
    user_type: "Website User",
    connected: true,
    rooms: new Set(),
    nsp: namespace,

    on(event, callback) {
      listeners.set(event, callback);
    },

    emit() {},

    join(room) {
      joins.push(room);
      if (!namespace.adapter.rooms.has(room)) {
        namespace.adapter.rooms.set(room, new Set());
      }
      namespace.adapter.rooms.get(room).add(this.id);
      this.rooms.add(room);
    },

    leave(room) {
      leaves.push(room);
      namespace.adapter.rooms.get(room)?.delete(this.id);
      this.rooms.delete(room);
    },
  };

  namespace.sockets.set(socket.id, socket);

  function frappeRequest(url, requestingSocket) {
    assert.equal(url, AUTHORITY);
    assert.equal(requestingSocket, socket);

    const request = {
      parameters: null,
      callback: null,
      responded: false,
    };

    requests.push(request);

    return {
      type(value) {
        assert.equal(value, "form");
        return this;
      },

      query(parameters) {
        request.parameters = parameters;
        return this;
      },

      end(callback) {
        // Deliberately do not deliver the response yet.
        request.callback = callback;
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
      return { frappe_request: frappeRequest, authorized_ticket_room_members: authorizedTicketRoomMembers };
    },

    console: { log() {} },
  };

  vm.runInNewContext(source, sandbox, { filename });
  assert.equal(typeof sandbox.module.exports, "function");

  sandbox.module.exports(namespace, socket);

  for (const event of [
    "doc_subscribe",
    "doc_unsubscribe",
    "doc_open",
    "doc_close",
    "disconnect",
  ]) {
    assert.equal(
      typeof listeners.get(event),
      "function",
      `Missing event handler: ${event}`
    );
  }

  // Ignore Frappe's initial user/website room registrations.
  joins.length = 0;

  function invoke(event, ticket) {
    listeners.get(event)("HD Ticket", ticket);
  }

  return {
    socket,
    namespace,
    requests,
    joins,
    leaves,

    start(path, ticket = "902") {
      invoke(path.start, ticket);
    },

    stop(path, ticket = "902") {
      invoke(path.stop, ticket);
    },

    disconnect() {
      socket.connected = false;
      listeners.get("disconnect")();
    },

    respond(index, ticket, { status = 200, message = true } = {}) {
      const request = requests[index];

      assert.ok(request, `Missing request ${index}`);
      assert.equal(typeof request.callback, "function");
      assert.equal(request.responded, false);
      assert.equal(request.parameters.ticket_name, ticket);
      assert.equal(request.parameters.channel, "native_doc");

      request.responded = true;
      request.callback(null, {
        status,
        body: { message },
      });
    },
  };
}

function assertNoProtectedJoin(h) {
  assert.deepEqual(
    h.joins.filter(
      (room) =>
        room.startsWith("doc:HD Ticket/") ||
        room.startsWith("open_doc:HD Ticket/")
    ),
    []
  );
}

function assertOneJoin(h, path, ticket = "902") {
  const room = path.room(ticket);

  assert.deepEqual(h.joins, [room]);
  assert.equal(
    h.namespace.adapter.rooms.get(room)?.has(h.socket.id),
    true
  );
}

let checked = 0;

function check(name, callback) {
  const harness = createHarness();

  callback(harness);

  checked += 1;
  console.log(
    `PASS ${String(checked).padStart(2, "0")} ${name}`
  );
}

for (const path of paths) {
  check(`${path.name}: approved request joins`, (h) => {
    h.start(path);
    assertNoProtectedJoin(h);

    h.respond(0, "902");

    assertOneJoin(h, path);
  });

  check(`${path.name}: stop before approval`, (h) => {
    h.start(path);
    h.stop(path);
    h.respond(0, "902");

    assertNoProtectedJoin(h);
  });

  check(`${path.name}: disconnect before approval`, (h) => {
    h.start(path);
    h.disconnect();
    h.respond(0, "902");

    assertNoProtectedJoin(h);
  });

  check(`${path.name}: disconnected state prevents join`, (h) => {
    h.start(path);
    h.socket.connected = false;
    h.respond(0, "902");

    assertNoProtectedJoin(h);
  });

  check(`${path.name}: older response arrives first`, (h) => {
    h.start(path);
    h.start(path);

    assert.equal(h.requests.length, 2);

    h.respond(0, "902");
    assertNoProtectedJoin(h);

    h.respond(1, "902");
    assertOneJoin(h, path);
  });

  check(`${path.name}: older response arrives last`, (h) => {
    h.start(path);
    h.start(path);

    h.respond(1, "902");
    assertOneJoin(h, path);

    h.respond(0, "902");
    assertOneJoin(h, path);
  });

  check(`${path.name}: cancelled request followed by new request`, (h) => {
    h.start(path);
    h.stop(path);
    h.start(path);

    h.respond(0, "902");
    assertNoProtectedJoin(h);

    h.respond(1, "902");
    assertOneJoin(h, path);
  });

  check(`${path.name}: cancellation isolated by ticket`, (h) => {
    h.start(path, "902");
    h.start(path, "941");
    h.stop(path, "902");

    h.respond(0, "902");
    assertNoProtectedJoin(h);

    h.respond(1, "941");
    assertOneJoin(h, path, "941");
  });

  check(`${path.name}: denied request never joins`, (h) => {
    h.start(path);
    h.respond(0, "902", { status: 403, message: false });

    assertNoProtectedJoin(h);
  });

  check(`${path.name}: successful subscription can close`, (h) => {
    h.start(path);
    h.respond(0, "902");

    assertOneJoin(h, path);

    h.stop(path);

    assert.equal(
      h.namespace.adapter.rooms.get(path.room("902"))?.has(h.socket.id),
      false
    );

    assert.ok(h.leaves.includes(path.room("902")));
  });
}

// A pending doc: subscription must not be cancelled merely
// because the same ticket's open_doc: view was closed.
check("doc_close does not cancel doc_subscribe", (h) => {
  h.start(paths[0], "902");
  h.start(paths[1], "902");

  h.stop(paths[1], "902");

  h.respond(1, "902");
  assertNoProtectedJoin(h);

  h.respond(0, "902");
  assertOneJoin(h, paths[0]);
});

// Conversely, doc_unsubscribe must not cancel an open_doc: view.
check("doc_unsubscribe does not cancel doc_open", (h) => {
  h.start(paths[0], "902");
  h.start(paths[1], "902");

  h.stop(paths[0], "902");

  h.respond(0, "902");
  assertNoProtectedJoin(h);

  h.respond(1, "902");
  assertOneJoin(h, paths[1]);
});

assert.equal(checked, 22);

console.log();
console.log(`NATIVE_TICKET_LIFECYCLE_DECISIONS=${checked}`);
console.log("C3_154_NATIVE_TICKET_LIFECYCLE_BEHAVIOUR=PASS");

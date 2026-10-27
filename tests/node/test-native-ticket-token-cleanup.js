
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
  const trackedMaps = [];
  const requests = [];
  const joins = [];

  let failNextRequest = false;

  class TrackedMap extends Map {
    constructor(...args) {
      super(...args);
      trackedMaps.push(this);
    }
  }

  const namespace = {
    adapter: { rooms: new Map() },
    sockets: new Map(),

    to() {
      return { emit() {} };
    },
  };

  const socket = {
    id: "customer-socket",
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

    if (failNextRequest) {
      failNextRequest = false;
      throw new Error("Simulated synchronous request failure");
    }

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
    Map: TrackedMap,

    require(name) {
      assert.equal(name, "../utils");
      return { frappe_request: frappeRequest, authorized_ticket_room_members: authorizedTicketRoomMembers };
    },

    console: { log() {} },
  };

  vm.runInNewContext(source, sandbox, { filename });

  assert.equal(typeof sandbox.module.exports, "function");
  sandbox.module.exports(namespace, socket);

  assert.equal(
    trackedMaps.length,
    1,
    "Expected exactly one native pending-room registry"
  );

  for (const event of [
    "doc_subscribe",
    "doc_unsubscribe",
    "doc_open",
    "doc_close",
  ]) {
    assert.equal(
      typeof listeners.get(event),
      "function",
      `Missing native handler: ${event}`
    );
  }

  // Exclude Frappe's normal user/website room registrations.
  joins.length = 0;

  const registry = trackedMaps[0];

  function invoke(event, ticket) {
    listeners.get(event)("HD Ticket", ticket);
  }

  return {
    registry,
    requests,
    joins,

    start(path, ticket = "902") {
      invoke(path.start, ticket);
    },

    stop(path, ticket = "902") {
      invoke(path.stop, ticket);
    },

    failNextRequest() {
      failNextRequest = true;
    },

    respond(index, ticket, {
      status = 200,
      message = true,
      bodyPresent = true,
      responsePresent = true,
      error = null,
    } = {}) {
      const request = requests[index];

      assert.ok(request, `Missing request ${index}`);
      assert.equal(typeof request.callback, "function");
      assert.equal(request.responded, false);
      assert.equal(request.parameters.ticket_name, ticket);
      assert.equal(request.parameters.channel, "native_doc");

      request.responded = true;

      const response = responsePresent
        ? {
            status,
            ...(bodyPresent ? { body: { message } } : {}),
          }
        : null;

      request.callback(error, response);
    },
  };
}

function assertClean(h) {
  assert.equal(h.registry.size, 0, "Pending registry was not cleared");
  assert.deepEqual(h.joins, [], "Unexpected protected room join");
}

function assertApproved(h, path, ticket = "902") {
  assert.equal(h.registry.size, 0, "Approved token was not cleared");
  assert.deepEqual(h.joins, [path.room(ticket)]);
}

let checked = 0;

function check(name, callback) {
  const h = createHarness();
  callback(h);

  checked += 1;

  console.log(
    `PASS ${String(checked).padStart(2, "0")} ${name}`
  );
}

for (const path of paths) {
  const room = path.room("902");

  check(`${path.name}: approval clears token`, (h) => {
    h.start(path);

    assert.equal(h.registry.size, 1);
    assert.equal(h.registry.has(room), true);

    h.respond(0, "902");
    assertApproved(h, path);
  });

  check(`${path.name}: HTTP 403 clears token`, (h) => {
    h.start(path);
    h.respond(0, "902", {
      status: 403,
      message: false,
    });

    assertClean(h);
  });

  check(`${path.name}: HTTP 500 clears token`, (h) => {
    h.start(path);
    h.respond(0, "902", { status: 500 });

    assertClean(h);
  });

  check(`${path.name}: boolean false clears token`, (h) => {
    h.start(path);
    h.respond(0, "902", { message: false });

    assertClean(h);
  });

  check(`${path.name}: missing response clears token`, (h) => {
    h.start(path);
    h.respond(0, "902", { responsePresent: false });

    assertClean(h);
  });

  check(`${path.name}: transport failure clears token`, (h) => {
    h.start(path);
    h.respond(0, "902", {
      error: new Error("Transport failure"),
    });

    assertClean(h);
  });

  check(`${path.name}: synchronous failure clears token`, (h) => {
    h.failNextRequest();
    h.start(path);

    assert.equal(h.requests.length, 1);
    assertClean(h);
  });

  check(`${path.name}: older denial preserves newer token`, (h) => {
    h.start(path);
    h.start(path);

    assert.equal(h.requests.length, 2);

    const latestToken = h.registry.get(room);
    assert.ok(latestToken);

    h.respond(0, "902", {
      status: 403,
      message: false,
    });

    assert.equal(h.registry.get(room), latestToken);
    assert.deepEqual(h.joins, []);

    h.respond(1, "902");
    assertApproved(h, path);
  });

  check(`${path.name}: newer denial blocks older approval`, (h) => {
    h.start(path);
    h.start(path);

    h.respond(1, "902", {
      status: 403,
      message: false,
    });

    assertClean(h);

    h.respond(0, "902");
    assertClean(h);
  });

  check(`${path.name}: cancelled denial preserves replacement`, (h) => {
    h.start(path);
    h.stop(path);
    h.start(path);

    const replacementToken = h.registry.get(room);
    assert.ok(replacementToken);

    h.respond(0, "902", {
      status: 403,
      message: false,
    });

    assert.equal(h.registry.get(room), replacementToken);
    assert.deepEqual(h.joins, []);

    h.respond(1, "902");
    assertApproved(h, path);
  });

  check(`${path.name}: cleanup isolated by ticket`, (h) => {
    h.start(path, "902");
    h.start(path, "941");

    assert.equal(h.registry.size, 2);

    const otherRoom = path.room("941");
    const otherToken = h.registry.get(otherRoom);

    h.respond(0, "902", {
      status: 403,
      message: false,
    });

    assert.equal(h.registry.size, 1);
    assert.equal(h.registry.has(room), false);
    assert.equal(h.registry.get(otherRoom), otherToken);
    assert.deepEqual(h.joins, []);

    h.respond(1, "941");
    assertApproved(h, path, "941");
  });
}

assert.equal(checked, 22);

console.log();
console.log(`NATIVE_TICKET_TOKEN_CLEANUP_DECISIONS=${checked}`);
console.log("C3_157_NATIVE_TOKEN_CLEANUP_BEHAVIOUR=PASS");

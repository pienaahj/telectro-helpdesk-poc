
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const filename = process.argv[2];
assert.ok(filename, "Patched Helpdesk handler filename required");

const source = fs.readFileSync(filename, "utf8");

const ENDPOINT =
  "/api/method/telephony.realtime_ticket_authorization.require_ticket_realtime_access";

const roomFor = (ticket) => `open_doc:HD Ticket/${ticket}`;

function createHarness() {
  const listeners = new Map();
  const requests = [];
  const joins = [];
  const leaves = [];
  const broadcasts = [];

  const namespace = {
    adapter: { rooms: new Map() },
    sockets: new Map(),

    to(room) {
      return {
        emit(event, payload) {
          broadcasts.push({ room, event, payload });
        },
      };
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

    emit(event, payload) { broadcasts.push({ room: roomFor(payload.ticket_id), event, payload }); },

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
    assert.equal(url, ENDPOINT);
    assert.equal(requestingSocket, socket);

    const request = {
      parameters: null,
      callback: null,
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
        // Intentionally defer the HTTP response.
        request.callback = callback;
        return this;
      },
    };
  }

async function authorizedTicketRoomMembers(ns, room, ticket, channel) {
    assert.equal(ns, namespace);
    assert.equal(channel, "helpdesk_ticket");
    assert.equal(room, `open_doc:HD Ticket/${ticket}`);
    return [...(ns.adapter.rooms.get(room) || [])]
      .map(id => ns.sockets.get(id))
      .filter(sock => sock && sock.connected === true && sock.rooms?.has(room));
  }

  const sandbox = {
    module: { exports: {} },

    require(name) {
      assert.equal(name, "../../frappe/realtime/utils");
      return { frappe_request: frappeRequest, authorized_ticket_room_members: authorizedTicketRoomMembers };
    },

    console: { log() {} },
  };

  vm.runInNewContext(source, sandbox, { filename });
  assert.equal(typeof sandbox.module.exports, "function");

  sandbox.module.exports(socket);

  for (const event of [
    "view_ticket",
    "stop_view_ticket",
    "disconnect",
  ]) {
    assert.equal(
      typeof listeners.get(event),
      "function",
      `Missing ${event} listener`
    );
  }

  return {
    socket,
    requests,
    joins,
    leaves,
    broadcasts,

    view(ticket) {
      return listeners.get("view_ticket")(ticket);
    },

    stop(ticket) {
      listeners.get("stop_view_ticket")(ticket);
    },

    disconnect() {
      socket.connected = false;
      listeners.get("disconnect")();
    },

    approve(index, ticket) {
      const request = requests[index];

      assert.ok(request, `Missing HTTP request ${index}`);
      assert.equal(typeof request.callback, "function");
      assert.equal(request.parameters.ticket_name, ticket);
      assert.equal(request.parameters.channel, "helpdesk_ticket");

      request.callback(null, {
        status: 200,
        body: { message: true },
      });
    },
  };
}

function expectNoJoin(harness) {
  assert.deepEqual(harness.joins, []);
  assert.deepEqual(harness.broadcasts, []);
}

function expectSingleJoin(harness, ticket) {
  const room = roomFor(ticket);

  assert.deepEqual(harness.joins, [room]);
  assert.equal(harness.broadcasts.length, 1);

  const notification = harness.broadcasts[0];

  assert.equal(notification.room, room);
  assert.equal(notification.event, "ticket_viewers");
  assert.equal(notification.payload.ticket_id, ticket);
  assert.equal(notification.payload.total_viewers, 1);

  assert.deepEqual(
    JSON.parse(notification.payload.users),
    ["test@boschendal.co.za"]
  );
}

let checked = 0;

async function check(name, run) {
  const harness = createHarness();

  await run(harness);
  await new Promise(resolve => setImmediate(resolve));

  checked += 1;
  console.log(
    `PASS ${String(checked).padStart(2, "0")} ${name}`
  );
}

async function main() {
  await check("Valid pending view joins after approval", async (h) => {
    const pending = h.view("902");

    assert.equal(h.requests.length, 1);
    expectNoJoin(h);

    h.approve(0, "902");
    await pending;
    await new Promise(resolve => setImmediate(resolve));

    expectSingleJoin(h, "902");
  });

  await check("Stop before approval prevents late join", async (h) => {
    const pending = h.view("902");

    h.stop("902");

    assert.deepEqual(h.leaves, []);
    expectNoJoin(h);

    h.approve(0, "902");
    await pending;
    await new Promise(resolve => setImmediate(resolve));

    expectNoJoin(h);
  });

  await check("Disconnect before approval prevents join", async (h) => {
    const pending = h.view("902");

    h.disconnect();

    h.approve(0, "902");
    await pending;
    await new Promise(resolve => setImmediate(resolve));

    expectNoJoin(h);
  });

  await check("Disconnected socket cannot join", async (h) => {
    const pending = h.view("902");

    // Connection state changes even without a disconnect event.
    h.socket.connected = false;

    h.approve(0, "902");
    await pending;
    await new Promise(resolve => setImmediate(resolve));

    expectNoJoin(h);
  });

  await check("Superseded first approval cannot join", async (h) => {
    const first = h.view("902");
    const second = h.view("902");

    assert.equal(h.requests.length, 2);

    h.approve(0, "902");
    await first;
    await new Promise(resolve => setImmediate(resolve));

    expectNoJoin(h);

    h.approve(1, "902");
    await second;
    await new Promise(resolve => setImmediate(resolve));

    expectSingleJoin(h, "902");
  });

  await check("Late superseded approval cannot rejoin", async (h) => {
    const first = h.view("902");
    const second = h.view("902");

    h.approve(1, "902");
    await second;
    await new Promise(resolve => setImmediate(resolve));

    expectSingleJoin(h, "902");

    h.approve(0, "902");
    await first;
    await new Promise(resolve => setImmediate(resolve));

    // The older response must not cause a second join.
    expectSingleJoin(h, "902");
  });

  await check("Cancelled view does not block a new view", async (h) => {
    const first = h.view("902");

    h.stop("902");

    const second = h.view("902");

    h.approve(0, "902");
    await first;
    await new Promise(resolve => setImmediate(resolve));

    expectNoJoin(h);

    h.approve(1, "902");
    await second;
    await new Promise(resolve => setImmediate(resolve));

    expectSingleJoin(h, "902");
  });

  await check("Cancellation is isolated per ticket", async (h) => {
    const first = h.view("902");
    const second = h.view("941");

    h.stop("902");

    h.approve(0, "902");
    await first;
    await new Promise(resolve => setImmediate(resolve));

    expectNoJoin(h);

    h.approve(1, "941");
    await second;
    await new Promise(resolve => setImmediate(resolve));

    expectSingleJoin(h, "941");
  });

  assert.equal(checked, 8);

  console.log();
  console.log(`HELPDESK_PENDING_VIEW_DECISIONS=${checked}`);
  console.log("C3_146_HELPDESK_PENDING_VIEW_BEHAVIOUR=PASS");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

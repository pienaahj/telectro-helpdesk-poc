
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const filename = process.argv[2];

assert.ok(filename, "Patched Helpdesk handler filename is required");

const source = fs.readFileSync(filename, "utf8");

const AUTHORITY_ENDPOINT =
  "/api/method/telephony.realtime_ticket_authorization.require_ticket_realtime_access";

async function simulate({
  ticket = "902",
  status = 200,
  message = true,
  bodyPresent = true,
  responsePresent = true,
  error = null,
  throwRequest = false,
} = {}) {
  const listeners = new Map();
  const joined = [];
  const requests = [];
  const broadcasts = [];

  const namespace = {
    adapter: {
      rooms: new Map(),
    },
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

    emit(event, payload) {
      broadcasts.push({
        room: `open_doc:HD Ticket/${ticket}`,
        event,
        payload,
      });
    },

    join(room) {
      joined.push(room);

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
    const request = {
      url,
      socket: requestingSocket,
      query: null,
    };

    requests.push(request);

    if (throwRequest) {
      throw new Error("Simulated request failure");
    }

    return {
      type() {
        return this;
      },

      query(parameters) {
        request.query = parameters;
        return this;
      },

      end(callback) {
        const response = responsePresent
          ? {
              status,
              ...(bodyPresent ? { body: { message } } : {}),
            }
          : null;

        callback(error, response);
        return this;
      },
    };
  }

  async function authorizedTicketRoomMembers(
    requestedNamespace,
    room,
    ticketName,
    channel
  ) {
    assert.equal(requestedNamespace, namespace);
    assert.equal(room, `open_doc:HD Ticket/${ticket}`);
    assert.equal(ticketName, ticket);
    assert.equal(channel, "helpdesk_ticket");

    return Array.from(
      requestedNamespace.adapter.rooms.get(room) || []
    )
      .map((id) => requestedNamespace.sockets.get(id))
      .filter(Boolean);
  }

  const sandbox = {
    module: { exports: {} },

    require(name) {
      assert.equal(
        name,
        "../../frappe/realtime/utils",
        "Unexpected Helpdesk dependency"
      );

      return {
        frappe_request: frappeRequest,
        authorized_ticket_room_members:
          authorizedTicketRoomMembers,
      };
    },

    console: {
      log() {},
    },
  };

  vm.runInNewContext(source, sandbox, { filename });

  assert.equal(typeof sandbox.module.exports, "function");

  sandbox.module.exports(socket);

  assert.ok(
    listeners.has("view_ticket"),
    "Missing Helpdesk view_ticket listener"
  );

  await listeners.get("view_ticket")(ticket);
  await new Promise((resolve) => setImmediate(resolve));
  return {
    ticket,
    socket,
    requests,
    joined,
    broadcasts,
  };
}

let checked = 0;

async function check(
  name,
  options,
  expectedAllowed,
  expectedRequests = 1
) {
  const result = await simulate(options);

  const room = `open_doc:HD Ticket/${result.ticket}`;

  assert.equal(
    result.joined.includes(room),
    expectedAllowed,
    `${name}: unexpected ticket room membership`
  );

  assert.equal(
    result.requests.length,
    expectedRequests,
    `${name}: unexpected permission request count`
  );

  if (expectedRequests === 1) {
    const request = result.requests[0];

    assert.equal(request.url, AUTHORITY_ENDPOINT);
    assert.equal(request.socket, result.socket);

    if (options.throwRequest) {
        // The simulated synchronous failure occurs before
        // .query() can populate the request parameters.
        assert.equal(
        request.query,
        null,
        `${name}: request should fail before query construction`
        );
    } else {
        assert.equal(request.query.ticket_name, result.ticket);
        assert.equal(request.query.channel, "helpdesk_ticket");
    }
   }

  if (expectedAllowed) {
    assert.equal(result.joined.length, 1);
    assert.equal(result.broadcasts.length, 1);

    const notification = result.broadcasts[0];

    assert.equal(notification.room, room);
    assert.equal(notification.event, "ticket_viewers");
    assert.equal(notification.payload.ticket_id, result.ticket);
    assert.equal(notification.payload.total_viewers, 1);

    assert.deepEqual(
      JSON.parse(notification.payload.users),
      ["test@boschendal.co.za"]
    );
  } else {
    assert.equal(
      result.joined.length,
      0,
      `${name}: denied request joined a room`
    );

    assert.equal(
      result.broadcasts.length,
      0,
      `${name}: denied request emitted viewer information`
    );
  }

  checked += 1;

  console.log(
    `PASS ${String(checked).padStart(2, "0")} ${name}`
  );
}

async function main() {
  await check(
    "Authorised Customer joins own ticket",
    {},
    true
  );

  await check(
    "Cross-Customer ticket denied",
    { ticket: "941", status: 403, message: false },
    false
  );

  await check(
    "HTTP 403 denied",
    { status: 403 },
    false
  );

  await check(
    "HTTP 500 denied",
    { status: 500 },
    false
  );

  await check(
    "Boolean false denied",
    { message: false },
    false
  );

  await check(
    "String true denied",
    { message: "true" },
    false
  );

  await check(
    "Missing response body denied",
    { bodyPresent: false },
    false
  );

  await check(
    "Missing HTTP response denied",
    { responsePresent: false },
    false
  );

  await check(
    "Transport error denied",
    { error: new Error("Connection failed") },
    false
  );

  await check(
    "Synchronous request failure denied",
    { throwRequest: true },
    false
  );

  await check(
    "Empty ticket rejected without HTTP request",
    { ticket: "" },
    false,
    0
  );

  await check(
    "Invalid ticket type rejected without HTTP request",
    { ticket: 902 },
    false,
    0
  );

  assert.equal(checked, 12);

  console.log();
  console.log(`HELPDESK_VIEW_TICKET_DECISIONS=${checked}`);
  console.log("C3_133_HELPDESK_ROOM_BEHAVIOUR=PASS");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});


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
  const requests = [];
  const broadcasts = [];
  const joined = [];

  const ticketRoom = `open_doc:HD Ticket/${ticket}`;

  // Deliberately populate the target room with a different user.
  // The requesting Customer has not joined this room.
  const existingViewer = {
    id: "existing-viewer",
    user: "ops.test@local.test",
    connected: true,
    rooms: new Set([ticketRoom]),
  };

  const namespace = {
    adapter: {
      rooms: new Map([
        [ticketRoom, new Set([existingViewer.id])],
      ]),
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
    id: "requesting-customer",
    user: "test@boschendal.co.za",
    user_type: "Website User",
    connected: true,
    rooms: new Set(),
    nsp: namespace,

    on(event, callback) {
      listeners.set(event, callback);
    },

    emit(event, payload) {
      broadcasts.push({ room: `socket:${this.id}`, event, payload });
    },

    join(room) {
      joined.push(room);
    },

    leave() {},
  };

  namespace.sockets.set(socket.id, socket);
  namespace.sockets.set(existingViewer.id, existingViewer);

  function frappeRequest(url, requestingSocket) {
    const request = {
      url,
      socket: requestingSocket,
      query: null,
    };

    requests.push(request);

    if (throwRequest) {
      throw new Error("Simulated synchronous request failure");
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

async function authorizedTicketRoomMembers(ns, room, ticket, channel) {
    assert.equal(ns, namespace);
    assert.equal(channel, "helpdesk_ticket");
    assert.equal(room, `open_doc:HD Ticket/${ticket}`);
    return [...(ns.adapter.rooms.get(room) || [])]
      .map(id => ns.sockets.get(id))
      .filter(sock => sock && sock.connected === true && sock.rooms?.has(room));
  }
  async function ticketAccessAllowed(sock, ticketName, channel) {
    assert.equal(sock, socket);
    assert.equal(ticketName, ticket);
    assert.equal(channel, "helpdesk_ticket");
    return status === 200 && !error && !throwRequest &&
      responsePresent && bodyPresent && message === true && sock.connected;
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
        authorized_ticket_room_members: authorizedTicketRoomMembers,
        ticket_access_allowed: ticketAccessAllowed,
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
    listeners.has("ticket_get_viewers"),
    "Missing ticket_get_viewers listener"
  );

  await listeners.get("ticket_get_viewers")(ticket);
  await new Promise(resolve => setImmediate(resolve));

  return {
    ticket,
    socket,
    requests,
    broadcasts,
    joined,
    ticketRoom,
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

  assert.equal(
    result.requests.length,
    expectedRequests,
    `${name}: unexpected permission request count`
  );

  // A viewer-query operation must never join a ticket room.
  assert.equal(
    result.joined.length,
    0,
    `${name}: viewer query unexpectedly joined a room`
  );

  if (expectedRequests === 1) {
    const request = result.requests[0];

    assert.equal(request.url, AUTHORITY_ENDPOINT);
    assert.equal(request.socket, result.socket);

    if (options.throwRequest) {
      assert.equal(
        request.query,
        null,
        `${name}: synchronous failure occurred after query setup`
      );
    } else {
      assert.equal(request.query.ticket_name, result.ticket);
      assert.equal(request.query.channel, "helpdesk_ticket");
    }
  }

  if (expectedAllowed) {
    assert.equal(
      result.broadcasts.length,
      1,
      `${name}: authorised viewer response missing`
    );

    const notification = result.broadcasts[0];

    assert.equal(
      notification.room,
      "socket:requesting-customer"
    );

    assert.equal(notification.event, "ticket_viewers");
    assert.equal(notification.payload.ticket_id, result.ticket);
    assert.equal(notification.payload.total_viewers, 1);

    assert.deepEqual(
      JSON.parse(notification.payload.users),
      ["ops.test@local.test"]
    );
  } else {
    // The ticket room exists and contains a viewer, but the
    // unauthorised caller must receive no viewer information.
    assert.equal(
      result.broadcasts.length,
      0,
      `${name}: unauthorised viewer information disclosed`
    );
  }

  checked += 1;

  console.log(
    `PASS ${String(checked).padStart(2, "0")} ${name}`
  );
}

async function main() {
  await check(
    "Authorised ticket viewer query",
    {},
    true
  );

  await check(
    "Cross-Customer ticket viewer query denied",
    { ticket: "941", status: 403, message: false },
    false
  );

  await check(
    "HTTP 403 viewer query denied",
    { status: 403 },
    false
  );

  await check(
    "HTTP 500 viewer query denied",
    { status: 500 },
    false
  );

  await check(
    "Boolean false viewer query denied",
    { message: false },
    false
  );

  await check(
    "String true viewer query denied",
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
    "Empty ticket rejected without request",
    { ticket: "" },
    false,
    0
  );

  await check(
    "Invalid ticket type rejected without request",
    { ticket: 902 },
    false,
    0
  );

  assert.equal(checked, 12);

  console.log();
  console.log(`HELPDESK_VIEWER_QUERY_DECISIONS=${checked}`);
  console.log("C3_135_HELPDESK_VIEWER_QUERY_BEHAVIOUR=PASS");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

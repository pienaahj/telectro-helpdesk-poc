
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const filename = process.argv[2];
assert.ok(filename, "Patched Helpdesk handler filename required");

const source = fs.readFileSync(filename, "utf8");

const ENDPOINT =
  "/api/method/telephony.realtime_ticket_authorization.require_ticket_realtime_access";

const EVENTS = [
  "helpdesk_ticket_typing",
  "helpdesk_ticket_typing_stopped",
];

async function simulate(event, options = {}) {
  const {
    ticket = "902",
    member = true,
    roomExists = true,
    otherTicketMember = false,
    status = 200,
    message = true,
    bodyPresent = true,
    responsePresent = true,
    error = null,
    throwRequest = false,
    leaveBeforeApproval = false,
  } = options;

  const listeners = new Map();
  const requests = [];
  const broadcasts = [];

  const room = `open_doc:HD Ticket/${ticket}`;

  const rooms = new Map();

  if (roomExists) {
    rooms.set(
      room,
      new Set(member ? ["customer-socket"] : [])
    );
  }

  if (otherTicketMember) {
    const otherTicket = ticket === "941" ? "902" : "941";
    rooms.set(
      `open_doc:HD Ticket/${otherTicket}`,
      new Set(["customer-socket"])
    );
  }

  const socket = {
    id: "customer-socket",
    user: "test@boschendal.co.za",
    user_type: "Website User",
    connected: true,
    rooms: new Set(member && roomExists ? [room] : []),

    nsp: {
      adapter: { rooms },
      sockets: new Map(),
    },

    on(name, callback) {
      listeners.set(name, callback);
    },

    emit() {},

    to(targetRoom) {
      return {
        emit(name, payload) {
          broadcasts.push({
            room: targetRoom,
            event: name,
            payload,
          });
        },
      };
    },
  };

  const observer = {
    id: "observer-socket", user: "ops.test@local.test", connected: true,
    rooms: new Set(roomExists ? [room] : []),
    emit(name, payload) {
      broadcasts.push({room, event: name, payload});
    },
  };
  if (roomExists) rooms.get(room).add(observer.id);
  socket.nsp.sockets.set(socket.id, socket);
  socket.nsp.sockets.set(observer.id, observer);

  async function deliverAuthorizedTicketRoom(ns, targetRoom, ticketName, channel, name, payload, excludedId) {
    assert.equal(ns, socket.nsp);
    assert.equal(targetRoom, room);
    assert.equal(ticketName, ticket);
    assert.equal(channel, "helpdesk_ticket");
    assert.equal(excludedId, socket.id);
    if (!socket.rooms.has(room)) return 0;
    for (const id of ns.adapter.rooms.get(room) || []) {
      const receiver = ns.sockets.get(id);
      if (receiver?.connected && receiver.rooms.has(room) && id !== excludedId) {
        receiver.emit(name, payload);
      }
    }
    return 1;
  }

  function frappeRequest(url, requestingSocket) {
    const request = {
      url,
      socket: requestingSocket,
      query: null,
    };

    requests.push(request);

    if (throwRequest) {
      throw new Error("Simulated synchronous HTTP failure");
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
        if (leaveBeforeApproval) {
            // Simulate the socket departing after the original
            // membership check but before HTTP approval completes.
            rooms.get(room)?.delete(socket.id);
        }
        callback(error, response);
        return this;
      },
    };
  }

  const sandbox = {
    module: { exports: {} },

    require(name) {
      assert.equal(
        name,
        "../../frappe/realtime/utils"
      );

      return {
        frappe_request: frappeRequest,
        deliver_authorized_ticket_room: deliverAuthorizedTicketRoom,
      };
    },

    console: { log() {} },
  };

  vm.runInNewContext(source, sandbox, { filename });

  sandbox.module.exports(socket);

  const handler = listeners.get(event);

  assert.equal(
    typeof handler,
    "function",
    `Missing ${event} handler`
  );

  await handler(ticket);

  return {
    socket,
    ticket,
    room,
    requests,
    broadcasts,
  };
}

let checked = 0;

async function check(event, name, options, expectedAllowed) {
  const result = await simulate(event, options);

  const validTicket =
    typeof result.ticket === "string" &&
    result.ticket.trim().length > 0;

  const isMember =
    options.member !== false &&
    options.roomExists !== false;

  const expectedRequests =
    validTicket && isMember ? 1 : 0;

  assert.equal(
    result.requests.length,
    expectedRequests,
    `${event}: ${name}: unexpected HTTP request count`
  );

  if (expectedRequests === 1) {
    const request = result.requests[0];

    assert.equal(request.url, ENDPOINT);
    assert.equal(request.socket, result.socket);

    if (options.throwRequest) {
      assert.equal(request.query, null);
    } else {
      assert.equal(request.query.ticket_name, result.ticket);
      assert.equal(request.query.channel, "helpdesk_ticket");
    }
  }

  if (expectedAllowed) {
    assert.equal(
      result.broadcasts.length,
      1,
      `${event}: ${name}: expected typing broadcast`
    );

    const notification = result.broadcasts[0];

    assert.equal(notification.room, result.room);
    assert.equal(notification.event, event);
    assert.equal(notification.payload.ticket_id, result.ticket);
    assert.equal(
      notification.payload.user,
      "test@boschendal.co.za"
    );

    assert.equal(
      Object.keys(notification.payload).sort().join(","),
      "ticket_id,user"
    );
  } else {
    assert.equal(
      result.broadcasts.length,
      0,
      `${event}: ${name}: unauthorised broadcast`
    );
  }

  checked += 1;

  console.log(
    `PASS ${String(checked).padStart(2, "0")} ` +
    `${event}: ${name}`
  );
}

async function main() {
  const cases = [
    [
      "Authorised current room member",
      {},
      true,
    ],
    [
        "Room left before authorisation completed",
        { leaveBeforeApproval: true },
        false,
    ],
    [
      "Non-member rejected",
      { member: false },
      false,
    ],
    [
      "Membership in another ticket rejected",
      { member: false, otherTicketMember: true },
      false,
    ],
    [
      "Missing ticket room rejected",
      { roomExists: false },
      false,
    ],
    [
      "Revoked ticket access rejected",
      { status: 403, message: false },
      false,
    ],
    [
      "HTTP 500 rejected",
      { status: 500 },
      false,
    ],
    [
      "Boolean false rejected",
      { message: false },
      false,
    ],
    [
      "String true rejected",
      { message: "true" },
      false,
    ],
    [
      "Missing response body rejected",
      { bodyPresent: false },
      false,
    ],
    [
      "Missing HTTP response rejected",
      { responsePresent: false },
      false,
    ],
    [
      "Transport failure rejected",
      { error: new Error("Connection failed") },
      false,
    ],
    [
      "Synchronous request failure rejected",
      { throwRequest: true },
      false,
    ],
    [
      "Empty ticket identity rejected",
      { ticket: "" },
      false,
    ],
    [
      "Non-string ticket identity rejected",
      { ticket: 902 },
      false,
    ],
  ];

  for (const event of EVENTS) {
    console.log();
    console.log(`=== ${event} ===`);

    for (const [name, options, expectedAllowed] of cases) {
      await check(event, name, options, expectedAllowed);
    }
  }

  assert.equal(checked, 30);

  console.log();
  console.log(`HELPDESK_TYPING_EVENT_DECISIONS=${checked}`);
  console.log("C3_142_HELPDESK_TYPING_BEHAVIOUR=PASS");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

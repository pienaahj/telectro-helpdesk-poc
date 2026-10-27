
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const filename = process.argv[2];
assert.ok(filename, "Patched Helpdesk handler filename is required");

const source = fs.readFileSync(filename, "utf8");

function simulate({
  ticket = "902",
  isMember = false,
  roomExists = true,
  otherViewer = true,
  memberOfOtherTicket = false,
} = {}) {
  const listeners = new Map();
  const leaves = [];
  const broadcasts = [];

  const targetRoom = `open_doc:HD Ticket/${ticket}`;
  const otherRoom = "open_doc:HD Ticket/941";

  const customer = {
    id: "customer-socket",
    user: "test@boschendal.co.za",
    connected: true,
    rooms: new Set(),
  };

  const observer = {
    id: "observer-socket",
    user: "ops.test@local.test",
    connected: true,
    rooms: new Set(),
    emit(event, payload) { broadcasts.push({room:`socket:${this.id}`,event,payload}); },
  };

  const rooms = new Map();

  if (roomExists) {
    const members = new Set();

    if (isMember) members.add(customer.id);
    if (otherViewer) members.add(observer.id);

    rooms.set(targetRoom, members);
    if (isMember) customer.rooms.add(targetRoom);
    if (otherViewer) observer.rooms.add(targetRoom);
  }

  if (memberOfOtherTicket) {
    rooms.set(otherRoom, new Set([customer.id]));
    customer.rooms.add(otherRoom);
  }

  const namespace = {
    adapter: { rooms },

    sockets: new Map([
      [customer.id, customer],
      [observer.id, observer],
    ]),

    to(room) {
      return {
        emit(event, payload) {
          broadcasts.push({ room, event, payload });
        },
      };
    },
  };

  const socket = {
    ...customer,
    nsp: namespace,

    on(event, callback) {
      listeners.set(event, callback);
    },

    emit(event, payload) {
      broadcasts.push({ room: `socket:${this.id}`, event, payload });
    },

    leave(room) {
      leaves.push(room);
      rooms.get(room)?.delete(this.id);
      this.rooms.delete(room);
    },
  };

  namespace.sockets.set(socket.id, socket);

  async function authorizedTicketRoomMembers(ns, room, ticketName, channel) {
    assert.equal(ns, namespace);
    assert.equal(room, `open_doc:HD Ticket/${ticketName}`);
    assert.equal(channel, "helpdesk_ticket");
    return [...(ns.adapter.rooms.get(room) || [])]
      .map(id => ns.sockets.get(id))
      .filter(sock => sock && sock.connected && sock.rooms.has(room));
  }

  const sandbox = {
    module: { exports: {} },

    require(name) {
      assert.equal(name, "../../frappe/realtime/utils");

      return {
        authorized_ticket_room_members: authorizedTicketRoomMembers,
        frappe_request() {
          throw new Error(
            "stop_view_ticket must not require an HTTP request"
          );
        },
      };
    },

    console: { log() {} },
  };

  vm.runInNewContext(source, sandbox, { filename });

  assert.equal(typeof sandbox.module.exports, "function");

  sandbox.module.exports(socket);

  const handler = listeners.get("stop_view_ticket");

  assert.equal(
    typeof handler,
    "function",
    "Missing stop_view_ticket handler"
  );

  handler(ticket);


  return {
    ticket,
    socket,
    targetRoom,
    otherRoom,
    rooms,
    leaves,
    broadcasts,
  };
}

let checked = 0;

async function check(name, options, expectedAllowed) {
  const result = simulate(options);
  await new Promise(resolve => setImmediate(resolve));

  if (expectedAllowed) {
    assert.deepEqual(
      result.leaves,
      [result.targetRoom],
      `${name}: legitimate viewer did not leave`
    );

    assert.equal(
      result.rooms.get(result.targetRoom).has(result.socket.id),
      false,
      `${name}: socket remains in ticket room`
    );

    assert.equal(
      result.broadcasts.length,
      options.otherViewer === false ? 0 : 1,
      `${name}: unexpected viewer notification recipients`
    );
    // With no remaining room member, no socket should receive a notification.
    if (options.otherViewer === false) {
      checked += 1;
      console.log(`PASS ${String(checked).padStart(2, "0")} ${name}`);
      return;
    }

    const notification = result.broadcasts[0];

    assert.equal(notification.room, "socket:observer-socket");
    assert.equal(notification.event, "ticket_viewers");
    assert.equal(notification.payload.ticket_id, result.ticket);

    const expectedUsers =
      options.otherViewer === false
        ? []
        : ["ops.test@local.test"];

    assert.deepEqual(
      JSON.parse(notification.payload.users),
      expectedUsers
    );

    assert.equal(
      notification.payload.total_viewers,
      expectedUsers.length
    );
  } else {
    assert.equal(
      result.leaves.length,
      0,
      `${name}: unauthorised room-leave attempted`
    );

    assert.equal(
      result.broadcasts.length,
      0,
      `${name}: unauthorised viewer notification emitted`
    );

    if (options.otherViewer !== false && options.roomExists !== false) {
      assert.equal(
        result.rooms.get(result.targetRoom).has("observer-socket"),
        true,
        `${name}: existing viewer membership changed`
      );
    }

    if (options.memberOfOtherTicket) {
      assert.equal(
        result.rooms.get(result.otherRoom).has(result.socket.id),
        true,
        `${name}: unrelated ticket membership changed`
      );
    }
  }

  checked += 1;
  console.log(
    `PASS ${String(checked).padStart(2, "0")} ${name}`
  );
}

async function main() {
await check(
  "Legitimate viewer leaves and notifies remaining viewers",
  { isMember: true },
  true
);

await check(
  "Unrelated Customer cannot trigger viewer notification",
  { isMember: false },
  false
);

await check(
  "Membership in a different ticket grants no authority",
  { isMember: false, memberOfOtherTicket: true },
  false
);

await check(
  "Missing ticket room produces no notification",
  { isMember: false, roomExists: false },
  false
);

await check(
  "Empty ticket identity is rejected",
  { ticket: "", isMember: false, roomExists: false },
  false
);

await check(
  "Last legitimate viewer can leave",
  { isMember: true, otherViewer: false },
  true
);

assert.equal(checked, 6);

console.log();
console.log(`HELPDESK_STOP_VIEW_DECISIONS=${checked}`);
console.log("C3_140_HELPDESK_STOP_VIEW_BEHAVIOUR=PASS");

}
main().catch(err => { console.error(err); process.exitCode = 1; });

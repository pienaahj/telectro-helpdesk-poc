"use strict";

// Behavioural tests against the REAL generated utils.js, with only transport mocked.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = process.argv[2];
assert.ok(path, "generated utils.js path required");
const source = fs.readFileSync(path, "utf8");
const ENDPOINT = "/api/method/telephony.realtime_ticket_authorization.require_ticket_realtime_access";
const TICKET = "941";
const ROOM = "open_doc:HD Ticket/941";

function setup() {
  const requests = [];
  let throwGet = false;
  const mocks = {
    get(url) {
      if (throwGet) throw new Error("backend offline");
      const record = {url, headers: {}, params: {}, timeout: null, complete: null};
      requests.push(record);
      return {
        set(key, val) { record.headers[key] = val; return this; },
        type(kind) { assert.equal(kind, "form"); return this; },
        query(params) {Object.assign(record.params, params); return this;},
        timeout(params) {record.timeout = params; return this;},
        end(cb) {record.complete = cb; return this;},
      };
    },
  };
  const sandbox = {
    module: {exports: {}}, URL,
    require(name) {
      if (name === "superagent") return mocks;
      if (name === "../node_utils") return {get_conf: () => ({webserver_host:"backend", webserver_port:8000})};
      throw new Error(`Unexpected dependency: ${name}`);
    },
  };
  vm.runInNewContext(source, sandbox, {filename:path});
  const utils = sandbox.module.exports;
  const rooms = new Map([[ROOM, new Set()]]);
  const namespace = {adapter:{rooms}, sockets:new Map()};
  function add(id, {token=false, site=true}={}) {
    const received=[];
    const sock = {
      id, user:id, connected:true, rooms:new Set([ROOM]),
      site_name:site?"frontend":undefined,
      sid:token?undefined:`sid-${id}`,
      authorization_header:token?`token key-${id}:secret`:undefined,
      emit(event,payload) {received.push({event,payload});},
      leave(room) {this.rooms.delete(room); namespace.adapter.rooms.get(room)?.delete(this.id);},
    };
    namespace.sockets.set(id,sock);
    rooms.get(ROOM).add(id);
    return {sock,received};
  }
  function respond(idx, {status=200, message=true, error=null, missingBody=false}={}) {
    const rec=requests[idx];
    assert.ok(rec, `Request ${idx} absent`);
    assert.equal(rec.url, `http://backend:8000${ENDPOINT}`);
    assert.equal(rec.headers["X-Frappe-Site-Name"],"frontend");
    assert.equal(rec.params.ticket_name,TICKET);
    assert.equal(rec.params.channel,"helpdesk_ticket");
    assert.equal(rec.timeout.response,2000);
    assert.equal(rec.timeout.deadline,5000);
    rec.complete(error,{status,body:missingBody?undefined:{message}});
  }
  return {utils,requests,namespace,add,respond,setThrowGet(v){throwGet=v}};
}

async function flush() {await Promise.resolve(); await Promise.resolve();}
let passed=0;
async function check(name, run) {await run(); console.log(`PASS ${String(++passed).padStart(2,'0')} ${name}`);}

(async()=>{
  await check("currently authorised recipient receives payload",async()=>{
    const h=setup(), a=h.add("customer");
    const pending=h.utils.deliver_authorized_ticket_room(h.namespace,ROOM,TICKET,"helpdesk_ticket","ticket_update",{value:"ok"});
    assert.equal(h.requests.length,1);
    h.respond(0); await pending;
    assert.equal(a.received.length,1);
    assert.equal(a.received[0].event,"ticket_update");
    assert.equal(a.sock.rooms.has(ROOM),true);
  });
  await check("revoked recipient is evicted and receives nothing",async()=>{
    const h=setup(), a=h.add("revoked");
    const pending=h.utils.deliver_authorized_ticket_room(h.namespace,ROOM,TICKET,"helpdesk_ticket","ticket_update",{});
    h.respond(0,{status:403,message:false}); await pending;
    assert.deepEqual(a.received,[]); assert.equal(a.sock.rooms.has(ROOM),false);
  });
  await check("backend failure denies and evicts",async()=>{
    const h=setup(), a=h.add("backend-error");
    const pending=h.utils.deliver_authorized_ticket_room(h.namespace,ROOM,TICKET,"helpdesk_ticket","ticket_update",{});
    h.respond(0,{status:500}); await pending;
    assert.equal(a.received.length,0); assert.equal(a.sock.rooms.has(ROOM),false);
  });
  await check("false, string true, and missing response body all deny",async()=>{
    for(const config of [{message:false},{message:"true"},{missingBody:true}]) {
      const h=setup(), a=h.add("invalid-response");
      const pending=h.utils.deliver_authorized_ticket_room(h.namespace,ROOM,TICKET,"ticket_update",{},{});
      // Invalid channel never calls backend and fails closed.
      await pending;
      assert.equal(h.requests.length,0);
      assert.equal(a.received.length,0);
    }
    for(const config of [{message:false},{message:"true"},{missingBody:true}]) {
      const h=setup(), a=h.add("invalid-response");
      const pending=h.utils.deliver_authorized_ticket_room(h.namespace,ROOM,TICKET,"helpdesk_ticket","ticket_update",{});
      h.respond(0,config); await pending;
      assert.equal(a.received.length,0);
      assert.equal(a.sock.rooms.has(ROOM),false);
    }
  });
  await check("transport exception fails closed",async()=>{
    const h=setup(), a=h.add("transport-error"); h.setThrowGet(true);
    await h.utils.deliver_authorized_ticket_room(h.namespace,ROOM,TICKET,"helpdesk_ticket","ticket_update",{});
    assert.equal(a.received.length,0);assert.equal(a.sock.rooms.has(ROOM),false);
  });
  await check("missing site identity fails closed",async()=>{
    const h=setup(), a=h.add("bad-site",{site:false});
    await h.utils.deliver_authorized_ticket_room(h.namespace,ROOM,TICKET,"helpdesk_ticket","ticket_update",{});
    assert.equal(h.requests.length,0);assert.equal(a.sock.rooms.has(ROOM),false);
  });
  await check("disconnect during callback never delivers",async()=>{
    const h=setup(), a=h.add("gone");
    const pending=h.utils.deliver_authorized_ticket_room(h.namespace,ROOM,TICKET,"helpdesk_ticket","ticket_update",{});
    a.sock.connected=false;h.respond(0); await pending;
    assert.equal(a.received.length,0);
  });
  await check("leave during callback never delivers",async()=>{
    const h=setup(), a=h.add("left");
    const pending=h.utils.deliver_authorized_ticket_room(h.namespace,ROOM,TICKET,"helpdesk_ticket","ticket_update",{});
    a.sock.leave(ROOM);h.respond(0);await pending;
    assert.equal(a.received.length,0);
  });
  await check("excluded sender cannot receive typing event",async()=>{
    const h=setup(), a=h.add("sender"), b=h.add("recipient");
    const pending=h.utils.deliver_authorized_ticket_room(h.namespace,ROOM,TICKET,"helpdesk_ticket","typing",{},a.sock.id);
    assert.equal(h.requests.length,2);
    h.respond(0);h.respond(1);await pending;
    assert.equal(a.received.length,0);assert.equal(b.received.length,1);
  });
  await check("mixed recipients deliver only to those currently allowed",async()=>{
    const h=setup(), a=h.add("allowed"), b=h.add("revoked"), c=h.add("session-invalid");
    const pending=h.utils.deliver_authorized_ticket_room(h.namespace,ROOM,TICKET,"helpdesk_ticket","ticket_update",{});
    h.respond(0);h.respond(1,{status:403,message:false});h.respond(2,{status:403,message:false});await pending;
    assert.equal(a.received.length,1);
    assert.equal(b.received.length,0);assert.equal(c.received.length,0);
    assert.equal(b.sock.rooms.has(ROOM),false);assert.equal(c.sock.rooms.has(ROOM),false);
  });
  await check("native viewer notification does not evict Helpdesk-only room member",async()=>{
    const h=setup(), customer=h.add("helpdesk-customer");
    const pending=h.utils.authorized_ticket_room_members(
      h.namespace,ROOM,TICKET,"native_doc",false
    );
    assert.equal(h.requests.length,1);
    assert.equal(h.requests[0].params.channel,"native_doc");
    // Customer legitimately holds the Helpdesk room, but cannot use native_doc.
    h.requests[0].complete(null,{status:403,body:{message:false}});
    const members=await pending;
    assert.equal(members.length,0);
    assert.equal(customer.sock.rooms.has(ROOM),true);
    assert.equal(h.namespace.adapter.rooms.get(ROOM).has(customer.sock.id),true);
    assert.equal(customer.received.length,0);
  });
  await check("token session forwards token, not SID",async()=>{
    const h=setup(), a=h.add("token-user",{token:true});
    const pending=h.utils.deliver_authorized_ticket_room(h.namespace,ROOM,TICKET,"helpdesk_ticket","event",{});
    assert.equal(h.requests[0].headers.Authorization,"token key-token-user:secret");
    assert.equal(h.requests[0].params.sid,undefined);
    h.respond(0);await pending;
    assert.equal(a.received.length,1);
  });
  console.log(`REALTIME_RECIPIENT_DELIVERY_TESTS=${passed}/${passed} PASS`);
})().catch(err=>{console.error(err);process.exitCode=1;});

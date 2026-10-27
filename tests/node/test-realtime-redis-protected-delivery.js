"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const filename = process.argv[2];
assert.ok(filename, "Generated realtime index.js required");
const source = fs.readFileSync(filename,"utf8");

const protectedCalls = [];
const ordinaryEmits = [];
const broadCalls = [];
const listeners = new Map();
let redisEventHandler;
let broadcast;
const site = {
  use() {},
  on(event, fn) {listeners.set(event,fn);},
  emit(event, payload) {ordinaryEmits.push({room:"ALL",event,payload});},
  to(room) {return {emit(event,payload) {ordinaryEmits.push({room,event,payload});}};},
};
class FakeServer {
  constructor() {this.registrations = new Map();}
  of(namespace) {return site;}
}
const mockRedis = {
  async connect() {},
  subscribe(channel,cb) {assert.equal(channel,"events");redisEventHandler=cb;},
  async publish() {},
};
const sandbox = {
  module:{exports:{}},
  console:{log() {},error() {}},
  require(name) {
    if (name === "socket.io") return {Server:FakeServer};
    if (name === "node:http") return {createServer:()=>({listen(port,cb){cb();}})};
    if (name === "../node_utils") return {
      get_conf:()=>({socketio_port:9000}),get_redis_subscriber:()=>mockRedis,
    };
    if (name === "./utils") return {
      async deliver_authorized_hd_ticket_doctype(ns,room,event,payload) {
        assert.equal(ns,site);broadCalls.push({room,event,payload});
      },
      async deliver_authorized_ticket_room(ns,room,ticket,channel,event,payload) {
        assert.equal(ns,site);
        protectedCalls.push({room,ticket,channel,event,payload});
      },
    };
    if (name === "./middlewares/authenticate") return ()=>{};
    if (name === "./handlers/frappe_handlers") return ()=>{};
    if (name === "../../helpdesk/realtime/handlers") return ()=>{};
    throw new Error(`Unexpected dependency ${name}`);
  },
};
vm.runInNewContext(source,sandbox,{filename});
(async()=>{
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(typeof redisEventHandler,"function");
  const emit=async(room,event,payload)=>{
    await redisEventHandler(JSON.stringify({namespace:"frontend",room,event,message:payload}));
  };
  await emit("doc:HD Ticket/941","ticket_changed",{marker:"native"});
  await emit("open_doc:HD Ticket/941","ticket_changed",{marker:"helpdesk"});
  assert.equal(protectedCalls.length,2);
  assert.deepEqual(protectedCalls.map(x=>x.channel),["native_doc","helpdesk_ticket"]);
  assert.deepEqual(protectedCalls.map(x=>x.ticket),["941","941"]);
  assert.equal(ordinaryEmits.length,0);
  console.log("REDIS_PROTECTED_DOCUMENT_ROOMS=PASS");
  await emit("doc:Sales Invoice/INV-1","invoice_update",{safe:true});
  assert.equal(ordinaryEmits.length,1);
  assert.equal(ordinaryEmits[0].room,"doc:Sales Invoice/INV-1");
  console.log("REDIS_UNRELATED_DOCUMENT_PRESERVED=PASS");
  await emit("doctype:HD Ticket","list_update",{doctype:"HD Ticket",name:"941"});
  assert.equal(ordinaryEmits.length,1);
  assert.equal(broadCalls.length,1);
  assert.equal(broadCalls[0].room,"doctype:HD Ticket");
  console.log("REDIS_BROAD_HD_TICKET_PATH_PROTECTED=PASS");
  console.log("REDIS_PROTECTED_DELIVERY_TESTS=3/3 PASS");
})().catch(err=>{console.error(err);process.exitCode=1;});

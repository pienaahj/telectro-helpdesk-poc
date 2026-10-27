"use strict";
// Exercises the real generated native handler and shared recipient helper together.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const utilsFile=process.argv[2], handlerFile=process.argv[3];
assert.ok(utilsFile && handlerFile,"Generated utils.js and frappe_handlers.js required");
const utilsSource=fs.readFileSync(utilsFile,"utf8");
const handlerSource=fs.readFileSync(handlerFile,"utf8");
const ROOM="open_doc:HD Ticket/941";
const access={
  internal:true,
  observer:true,
  emerald:false,
};
const requests=[];
const superagent={
  get(url){
    const record={url,headers:{},params:{}};
    requests.push(record);
    return {
      set(k,v){record.headers[k]=v;return this;},
      type(){return this;},
      query(p){Object.assign(record.params,p);return this;},
      timeout(){return this;},
      end(cb){
        assert.equal(record.headers["X-Frappe-Site-Name"],"frontend");
        assert.equal(record.params.ticket_name,"941");
        const identity=record.params.sid;
        const allowed=record.params.channel==="helpdesk_ticket" || access[identity]===true;
        cb(allowed?null:new Error("denied"),{
          status:allowed?200:403,
          body:{message:allowed},
        });
        return this;
      },
    };
  },
};
const utilsSandbox={
  module:{exports:{}},URL,
  require(name){
    if(name==="superagent")return superagent;
    if(name==="../node_utils")return {get_conf:()=>({webserver_host:"backend",webserver_port:8000})};
    throw new Error(`Unexpected util require ${name}`);
  },
};
vm.runInNewContext(utilsSource,utilsSandbox,{filename:utilsFile});
const utils=utilsSandbox.module.exports;
const listeners=new Map(), rooms=new Map([[ROOM,new Set()]]), sockets=new Map();
const namespace={adapter:{rooms},sockets,to(){return {emit(){}}}};
function createSocket(id,userType="System User",captureListener=false){
  const received=[];
  const sock={
    id,user:id,user_type:userType,connected:true,site_name:"frontend",sid:id,
    nsp:namespace,rooms:new Set(),
    emit(event,payload){received.push({event,payload});},
    on(name,cb){if(captureListener)listeners.set(name,cb);},
    join(room){this.rooms.add(room);if(!rooms.has(room))rooms.set(room,new Set());rooms.get(room).add(id);},
    leave(room){this.rooms.delete(room);rooms.get(room)?.delete(id);},
  };
  sockets.set(id,sock);
  return {sock,received};
}
const internal=createSocket("internal","System User",true);
const observer=createSocket("observer");
const emerald=createSocket("emerald","Website User");
observer.sock.join(ROOM);
emerald.sock.join(ROOM);
const nativeSandbox={
  module:{exports:{}},
  require(name){assert.equal(name,"../utils");return utils;},
  console:{log(){}},
};
vm.runInNewContext(handlerSource,nativeSandbox,{filename:handlerFile});
nativeSandbox.module.exports(namespace,internal.sock);

(async()=>{
  listeners.get("doc_open")("HD Ticket","941");
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(internal.sock.rooms.has(ROOM),true);
  assert.equal(emerald.sock.rooms.has(ROOM),true,"native notification evicted authorised Helpdesk viewer");
  assert.equal(emerald.received.length,0,"native-only viewer list leaked to Customer");
  assert.equal(observer.received.some(x=>x.event==="doc_viewers"),true);
  console.log("SHARED_ROOM_NATIVE_VIEWERS_ISOLATED=PASS");

  await utils.deliver_authorized_ticket_room(namespace,ROOM,"941","helpdesk_ticket","ticket_update",{probe:"C3-234"});
  assert.equal(emerald.received.some(x=>x.event==="ticket_update"),true);
  assert.equal(emerald.sock.rooms.has(ROOM),true);
  console.log("SHARED_ROOM_HELPDESK_ACCESS_PRESERVED=PASS");
  console.log("NATIVE_HELPDESK_SHARED_ROOM_TESTS=2/2 PASS");
})().catch(err=>{console.error(err);process.exitCode=1;});

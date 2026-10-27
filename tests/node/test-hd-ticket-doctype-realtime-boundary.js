"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const utilsFile = process.argv[2];
const handlersFile = process.argv[3];
assert.ok(utilsFile && handlersFile, "generated utils.js and native handlers.js required");
const utilsSource = fs.readFileSync(utilsFile,"utf8");
const handlersSource = fs.readFileSync(handlersFile,"utf8");
let passed=0;
async function check(name,fn){await fn();console.log(`PASS ${String(++passed).padStart(2,"0")} ${name}`);}

function handlerHarness({userType="Website User",status=200,deferred=false}={}) {
  const listeners=new Map(),requests=[],joined=[],internalChecks=[];
  const ns={adapter:{rooms:new Map()},sockets:new Map(),to(){return {emit(){}}}};
  const socket={id:"one",user:"demo@example.com",user_type:userType,connected:true,
    nsp:ns,rooms:new Set(),on(event,cb){listeners.set(event,cb)},emit(){},
    join(room){joined.push(room);this.rooms.add(room);if(!ns.adapter.rooms.has(room))ns.adapter.rooms.set(room,new Set());ns.adapter.rooms.get(room).add(this.id);},
    leave(room){this.rooms.delete(room);ns.adapter.rooms.get(room)?.delete(this.id)},
  };
  ns.sockets.set(socket.id,socket);
  const frappe_request=(url,sock)=>{
    assert.equal(sock,socket);
    const rec={url,params:null,callback:null};requests.push(rec);
    return {type(){return this},query(params){rec.params=params;return this},end(cb){rec.callback=cb;cb(null,{status:200,body:{message:true}});return this}};
  };
  const hd_ticket_doctype_access_allowed=(sock)=>new Promise(resolve=>{
    assert.equal(sock,socket);
    internalChecks.push(resolve);
    if(!deferred)resolve(status===200);
  });
  const sandbox={module:{exports:{}},console:{log(){}},require(name){
    assert.equal(name,"../utils");return {
      frappe_request,hd_ticket_doctype_access_allowed,
      async authorized_ticket_room_members(){return []}
    };
  }};
  vm.runInNewContext(handlersSource,sandbox,{filename:handlersFile});
  sandbox.module.exports(ns,socket);
  return {socket,listeners,requests,joined,internalChecks,
    respond(i,allowed=true){assert.ok(internalChecks[i]);internalChecks[i](allowed)}};
}

function deliveryHarness(){
  const calls=[],ns={adapter:{rooms:new Map([["doctype:HD Ticket",new Set()]])},sockets:new Map()};
  let throwRequest=false;
  const request={get(url){if(throwRequest)throw Error("network failure");
    const rec={url,headers:{},params:{},callback:null};calls.push(rec);
    return {set(k,v){rec.headers[k]=v;return this},type(){return this},timeout(t){rec.timeout=t;return this},query(params){Object.assign(rec.params,params);return this},end(cb){rec.callback=cb;return this}};
  }};
  const sandbox={module:{exports:{}},URL,require(name){
    if(name==="superagent")return request;
    if(name==="../node_utils")return {get_conf:()=>({webserver_host:"backend",webserver_port:8000})};
    throw Error(`Unexpected require ${name}`);
  }};
  vm.runInNewContext(utilsSource,sandbox,{filename:utilsFile});
  const utils=sandbox.module.exports,room="doctype:HD Ticket";
  function add(id,{userType="System User",site=true,token=false}={}){
    const received=[];
    const sock={id,user:id,user_type:userType,connected:true,rooms:new Set([room]),site_name:site?"frontend":undefined,
      sid:token?null:`sid-${id}`,authorization_header:token?`token ${id}:secret`:null,
      emit(event,payload){received.push({event,payload})},leave(r){this.rooms.delete(r);ns.adapter.rooms.get(r)?.delete(this.id)}};
    ns.sockets.set(id,sock);ns.adapter.rooms.get(room).add(id);
    return {sock,received};
  }
  function answer(i,message,{status=200,error=null,missingBody=false}={}){
    const rec=calls[i];assert.ok(rec,`request ${i} missing`);
    rec.callback(error,{status,body:missingBody?undefined:{message}});
  }
  return {utils,ns,calls,add,answer,setThrow(v){throwRequest=v}};
}
async function flush(){await new Promise(resolve=>setImmediate(resolve));}
(async()=>{
  await check("Website User cannot subscribe to unscoped HD Ticket",async()=>{
    const h=handlerHarness();h.listeners.get("doctype_subscribe")("HD Ticket");await flush();
    assert.equal(h.internalChecks.length,0);assert.equal(h.socket.rooms.has("doctype:HD Ticket"),false);
  });
  await check("System User joins after Telectro internal authority approves",async()=>{
    const h=handlerHarness({userType:"System User"});h.listeners.get("doctype_subscribe")("HD Ticket");await flush();
    assert.equal(h.internalChecks.length,1);
    assert.equal(h.requests.length,0,"Do not use general Frappe DocType read check");
    assert.equal(h.socket.rooms.has("doctype:HD Ticket"),true);
  });
  await check("Partner System User rejected by internal backend authority",async()=>{
    const h=handlerHarness({userType:"System User",status:403});h.listeners.get("doctype_subscribe")("HD Ticket");await flush();
    assert.equal(h.internalChecks.length,1);
    assert.equal(h.socket.rooms.has("doctype:HD Ticket"),false);
  });
  await check("Unsubscribe cancels in-flight internal approval",async()=>{
    const h=handlerHarness({userType:"System User",deferred:true});h.listeners.get("doctype_subscribe")("HD Ticket");await flush();
    h.listeners.get("doctype_unsubscribe")("HD Ticket");h.respond(0);await flush();
    assert.equal(h.socket.rooms.has("doctype:HD Ticket"),false);
  });
  await check("Disconnect cancels in-flight internal approval",async()=>{
    const h=handlerHarness({userType:"System User",deferred:true});h.listeners.get("doctype_subscribe")("HD Ticket");await flush();
    h.socket.connected=false;h.listeners.get("disconnect")();h.respond(0);await flush();
    assert.equal(h.socket.rooms.has("doctype:HD Ticket"),false);
  });
  await check("Other DocType behavior preserved for Website User",async()=>{
    const h=handlerHarness();h.listeners.get("doctype_subscribe")("Customer");
    assert.equal(h.requests.length,1);assert.equal(h.socket.rooms.has("doctype:Customer"),true);
  });
  await check("Newer subscription supersedes stale internal approval",async()=>{
    const h=handlerHarness({userType:"System User",deferred:true});h.listeners.get("doctype_subscribe")("HD Ticket");
    await flush();h.listeners.get("doctype_subscribe")("HD Ticket");await flush();
    h.respond(0);await flush();assert.equal(h.socket.rooms.has("doctype:HD Ticket"),false);
    h.respond(1);await flush();assert.equal(h.socket.rooms.has("doctype:HD Ticket"),true);
  });
  await check("Current System User receives event after identity and read recheck",async()=>{
    const h=deliveryHarness(),a=h.add("ops");
    const pending=h.utils.deliver_authorized_hd_ticket_doctype(h.ns,"doctype:HD Ticket","list_update",{name:"941"});
    assert.equal(h.calls.length,1);assert.ok(h.calls[0].url.endsWith("/frappe.realtime.get_user_info"));
    h.answer(0,{user:"ops",user_type:"System User"});await flush();
    assert.equal(h.calls.length,2);
    assert.ok(h.calls[1].url.endsWith("/telephony.realtime_ticket_authorization.require_internal_hd_ticket_doctype_realtime_access"));
    assert.equal(h.calls[1].params.doctype,undefined);
    h.answer(1,true);assert.equal(await pending,1);assert.equal(a.received.length,1);
  });
  await check("Previously joined Website User is evicted without backend request",async()=>{
    const h=deliveryHarness(),a=h.add("customer",{userType:"Website User"});
    assert.equal(await h.utils.deliver_authorized_hd_ticket_doctype(h.ns,"doctype:HD Ticket","list_update",{}),0);
    assert.equal(h.calls.length,0);assert.equal(a.received.length,0);assert.equal(a.sock.rooms.has("doctype:HD Ticket"),false);
  });
  await check("Partner System User with DocType read but without internal authority is evicted",async()=>{
    const h=deliveryHarness(),partner=h.add("partner",{userType:"System User"});
    const pending=h.utils.deliver_authorized_hd_ticket_doctype(h.ns,"doctype:HD Ticket","list_update",{name:"941"});
    h.answer(0,{user:"partner",user_type:"System User"});await flush();
    assert.ok(h.calls[1].url.includes("require_internal_hd_ticket_doctype_realtime_access"));
    h.answer(1,null,{status:403});
    assert.equal(await pending,0);
    assert.equal(partner.received.length,0);
    assert.equal(partner.sock.rooms.has("doctype:HD Ticket"),false);
  });
  await check("Expired SID Guest identity denies and evicts",async()=>{
    const h=deliveryHarness(),a=h.add("revoked");
    const pending=h.utils.deliver_authorized_hd_ticket_doctype(h.ns,"doctype:HD Ticket","list_update",{});
    h.answer(0,{user:"Guest",user_type:"Website User"});await pending;
    assert.equal(h.calls.length,1);assert.equal(a.received.length,0);assert.equal(a.sock.rooms.has("doctype:HD Ticket"),false);
  });
  await check("Account changed from System User to Website User denies",async()=>{
    const h=deliveryHarness(),a=h.add("demoted");
    const pending=h.utils.deliver_authorized_hd_ticket_doctype(h.ns,"doctype:HD Ticket","list_update",{});
    h.answer(0,{user:"demoted",user_type:"Website User"});await pending;
    assert.equal(a.received.length,0);assert.equal(a.sock.rooms.has("doctype:HD Ticket"),false);
  });
  await check("Current internal authority denial evicts recipient",async()=>{
    const h=deliveryHarness(),a=h.add("read-revoked");
    const pending=h.utils.deliver_authorized_hd_ticket_doctype(h.ns,"doctype:HD Ticket","list_update",{});
    h.answer(0,{user:"read-revoked",user_type:"System User"});await flush();
    h.answer(1,false,{status:403});await pending;
    assert.equal(a.received.length,0);assert.equal(a.sock.rooms.has("doctype:HD Ticket"),false);
  });
  await check("Backend exception fails closed",async()=>{
    const h=deliveryHarness(),a=h.add("network-error");h.setThrow(true);
    assert.equal(await h.utils.deliver_authorized_hd_ticket_doctype(h.ns,"doctype:HD Ticket","list_update",{}),0);
    assert.equal(a.received.length,0);assert.equal(a.sock.rooms.has("doctype:HD Ticket"),false);
  });
  await check("Membership lost during callback does not deliver",async()=>{
    const h=deliveryHarness(),a=h.add("left");
    const pending=h.utils.deliver_authorized_hd_ticket_doctype(h.ns,"doctype:HD Ticket","list_update",{});
    h.answer(0,{user:"left",user_type:"System User"});await flush();
    a.sock.leave("doctype:HD Ticket");h.answer(1,true);await pending;
    assert.equal(a.received.length,0);
  });
  await check("Token session rechecks using Authorization not SID",async()=>{
    const h=deliveryHarness(),a=h.add("token-user",{token:true});
    const pending=h.utils.deliver_authorized_hd_ticket_doctype(h.ns,"doctype:HD Ticket","list_update",{});
    assert.equal(h.calls[0].headers.Authorization,"token token-user:secret");assert.equal(h.calls[0].params.sid,undefined);
    h.answer(0,{user:"token-user",user_type:"System User"});await flush();h.answer(1,true);await pending;
    assert.equal(a.received.length,1);
  });
  await check("Mixed internal System and external Website members are separated",async()=>{
    const h=deliveryHarness(),good=h.add("ops"),bad=h.add("partner",{userType:"Website User"});
    const pending=h.utils.deliver_authorized_hd_ticket_doctype(h.ns,"doctype:HD Ticket","list_update",{name:"941"});
    assert.equal(h.calls.length,1);h.answer(0,{user:"ops",user_type:"System User"});await flush();h.answer(1,true);
    assert.equal(await pending,1);assert.equal(good.received.length,1);assert.equal(bad.received.length,0);
    assert.equal(bad.sock.rooms.has("doctype:HD Ticket"),false);
  });
  console.log(`HD_TICKET_DOCTYPE_BOUNDARY_TESTS=${passed}/${passed} PASS`);
})().catch(e=>{console.error(e);process.exitCode=1;});

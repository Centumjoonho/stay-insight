import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";
import { runInNewContext } from "node:vm";
import { JSDOM } from "jsdom";
import { act, createElement, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";
import * as helpers from "../src/lib/reservations.ts";
import * as contracts from "../src/lib/api/import-types.ts";
import { ApiError } from "../src/lib/api/transport.ts";
const require = createRequire(import.meta.url);
function load(path: string, dependencies: Record<string, unknown> = {}, extra: Record<string, unknown> = {}) {
  const exports = {};
  dependencies = { "next/link": {default:({href,children}:{href:string;children:ReactNode})=>createElement("a",{href},children)}, "@/lib/api/client": {businessApi:{}}, "@/lib/api/transport": {ApiError}, ...dependencies };
  runInNewContext(ts.transpileModule(readFileSync(new URL(path,import.meta.url),"utf8"), {
    compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022},
  }).outputText,{exports,Error,...extra,require:(name:string)=>dependencies[name] ?? require(name)});
  return exports;
}
const reservation: contracts.Reservation = {id:"res",property_id:"prop",external_reservation_id:"R1",import_id:"batch",origin:"CSV_IMPORT",version:2,manual_protected_fields:["room_units"],channel:"GENERIC",check_in:"2026-09-01",check_out:"2026-09-03",booked_nights:2,gross_revenue:"300000",channel_fee:null,net_revenue:null,guest_count:null,room_units:2,reservation_status:"CONFIRMED"};
function values() {const form=new FormData();for(const [k,v] of Object.entries(reservation)) if(v!==null) form.set(k,String(v));return form;}

test("reservation input validates and sends changed fields only",()=>{
  const form=values();const parsed=helpers.reservationValues(form);
  assert.deepEqual(helpers.changedReservationValues(parsed,reservation),{});
  form.set("room_units","3");assert.deepEqual(helpers.changedReservationValues(helpers.reservationValues(form),reservation),{room_units:3});
  form.set("channel_fee","400000");assert.throws(()=>helpers.reservationValues(form),/수수료/);
  form.set("channel_fee","");form.set("room_units","0");assert.throws(()=>helpers.reservationValues(form),/양의 정수/);
  form.set("room_units","");form.set("check_out","2026-08-01");assert.throws(()=>helpers.reservationValues(form),/체크아웃/);
});
test("history renders before/after, safe reasons, actor and protection release",()=>{
  const {ReservationHistory}=load("../src/components/reservation-editor.tsx",{"@/lib/reservations":helpers,"@/lib/api/import-types":contracts}) as typeof import("../src/components/reservation-editor");
  const html=renderToStaticMarkup(createElement(ReservationHistory,{total:1,items:[{id:"audit",event_type:"MANUAL_OVERRIDE_RELEASED",change_source:"MANUAL",actor_subject:"12345678-uuid",reservation_import_id:null,reason:"<script>bad</script>",changed_fields:["room_units"],before_values:{room_units:"MANUAL_PROTECTED"},after_values:{room_units:"CSV_MANAGED"},created_at:"2026-10-22T00:00:00Z"}]}));
  assert.ok(html.includes("CSV 보호 해제") && html.includes("12345678") && html.includes("CSV 갱신 허용"));
  assert.ok(!html.includes("<script>"));assert.ok(html.includes("<table"));
});
test("create edit cancel reopen release and stale conflict UI",async(t)=>{
  const dom=new JSDOM("<div id='root'></div>",{url:"http://localhost:3000"});
  const previous=new Map<string,PropertyDescriptor|undefined>();
  for(const [name,value] of Object.entries({window:dom.window,document:dom.window.document,HTMLElement:dom.window.HTMLElement,IS_REACT_ACT_ENVIRONMENT:true})) {
    previous.set(name,Object.getOwnPropertyDescriptor(globalThis,name));Object.defineProperty(globalThis,name,{configurable:true,writable:true,value});
  }
  const {createRoot}=await import("react-dom/client");const root=createRoot(dom.window.document.getElementById("root")!);
  t.after(async()=>{await act(async()=>root.unmount());dom.window.close();for(const [key,descriptor] of previous) if(descriptor)Object.defineProperty(globalThis,key,descriptor);else Reflect.deleteProperty(globalThis,key);});
  const calls:{kind:string;body:Record<string,unknown>}[]=[];let fail=false;
  const api={createReservation:async(_o:string,_p:string,body:Record<string,unknown>)=>{calls.push({kind:"create",body});return reservation;},updateReservation:async(_o:string,_r:string,body:Record<string,unknown>)=>{if(fail)throw new ApiError(409,"다른 변경이 먼저 저장되었습니다.");calls.push({kind:"edit",body});return reservation;},releaseReservation:async(_o:string,_r:string,body:Record<string,unknown>)=>{calls.push({kind:"release",body});return reservation;}};
  class BrowserFormData { private data: FormData; constructor(form: HTMLFormElement){this.data=new FormData();for(const e of Array.from(form.elements) as HTMLInputElement[]) if(e.name)this.data.set(e.name,e.value);}get(key:string){return this.data.get(key);} }
  const {ReservationEditor}=load("../src/components/reservation-editor.tsx",{"@/lib/reservations":helpers,"@/lib/api/import-types":contracts,"@/lib/api/transport":{ApiError},"@/lib/api/client":{businessApi:api},"next/navigation":{useRouter:()=>({replace:()=>{},refresh:()=>{}})}},{FormData:BrowserFormData,window:dom.window}) as typeof import("../src/components/reservation-editor");
  const doc=dom.window.document;
  const render=async(row?:contracts.Reservation,key="edit")=>act(async()=>root.render(createElement(ReservationEditor,{key,organizationId:"org",propertyId:"prop",reservation:row})));
  const fill=(name:string,value:string)=>{(doc.querySelector(`[name="${name}"]`) as HTMLInputElement).value=value;};
  const submit=async(label="예약 입력")=>act(async()=>{doc.querySelector(`form[aria-label="${label}"]`)!.dispatchEvent(new dom.window.Event("submit",{bubbles:true,cancelable:true}));});
  const click=async(text:string)=>act(async()=>{const b=[...doc.querySelectorAll("button")].find(b=>b.textContent?.includes(text));assert.ok(b,text);b.click();});
  await render(undefined,"create");for(const [k,v] of Object.entries(reservation)) if(doc.querySelector(`[name="${k}"]`) && v!==null)fill(k,String(v));await submit();assert.equal(calls[0].kind,"create");
  await render(reservation);fill("room_units","3");await submit();assert.match(doc.querySelector('[role="alert"]')!.textContent!,/변경 사유/);
  fill("change_reason","객실 수 확인");await submit();assert.equal(calls[1].body.room_units,3);assert.ok(!("gross_revenue" in calls[1].body));assert.ok(doc.body.textContent?.includes("수동 보정"));
  fill("reservation_status","CANCELLED");await submit();assert.equal(calls.at(-1)!.body.reservation_status,"CANCELLED");
  await render({...reservation,reservation_status:"CANCELLED"},"reopen");fill("change_reason","재개");fill("reservation_status","CONFIRMED");await submit();assert.equal(calls.at(-1)!.body.reservation_status,"CONFIRMED");
  await click("CSV 자동 갱신 허용");assert.ok(doc.body.textContent?.includes("현재 값은 즉시 바뀌지"));fill("reason","CSV 연동 재개");await submit("보호 해제 확인");assert.equal(calls.at(-1)!.kind,"release");
  fail=true;fill("room_units","3");await submit();assert.ok(doc.body.textContent?.includes("최신 예약 다시 불러오기"));assert.ok(doc.querySelector("fieldset")!.disabled);
  assert.ok(doc.querySelectorAll("label input").length>=6);
});

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";
import { runInNewContext } from "node:vm";
import { createElement, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";
import type { EventMarket } from "../src/lib/api/event-types.ts";

const require = createRequire(import.meta.url);
const exports = {};
runInNewContext(ts.transpileModule(readFileSync(new URL("../src/components/event-view.tsx", import.meta.url), "utf8"), {
 compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022 },
}).outputText, { exports, require: (name: string) => name === "next/link" ? { default: ({ href, children }: { href: string; children: ReactNode }) => createElement("a", { href }, children) } : require(name) });
const { EventView } = exports as typeof import("../src/components/event-view");
// SYNTHETIC API DTO FOR TESTS ONLY.
function fixture(): EventMarket {
 return { property_id:"test", available:true, reason:null, scope:{level:"SIGUNGU",name:"부산광역시 수영구"}, from_date:"2026-10-02",to_date:"2026-12-31",reference_date:"2026-10-02",
 events:[{source_event_id:"1",title:"TEST ONGOING",start_date:"2026-10-01",end_date:"2026-10-03",temporal_status:"ONGOING",address:"TEST ADDRESS",source_status:null,last_seen_at:"2026-10-02T00:00:00Z"},{source_event_id:"2",title:"TEST UPCOMING",start_date:"2026-10-05",end_date:"2026-10-06",temporal_status:"UPCOMING",address:null,source_status:"행사연기",last_seen_at:"2026-10-02T00:00:00Z"}],
 total_count:2,truncated:false,summary:{ongoing_count:1,next_30_days_count:1}, source:{provider:"한국관광공사",dataset:"국문 관광정보 서비스",url:"https://www.data.go.kr/data/15101578/openapi.do",collected_at:"2026-10-02T00:00:00Z",latest_sync_status:"COMPLETED",coverage_start:"2026-09-02",coverage_end:"2027-03-31"},warnings:[],source_category:"public" };
}
const render=(data:EventMarket|null)=>renderToStaticMarkup(createElement(EventView,{data}));
test("event list uses semantic dates, separate temporal/source status and coverage",()=>{
 const html=render(fixture());
 for(const text of ["공식 행사·축제","진행 중","예정","2026.10.01","TEST ADDRESS","행사연기","향후 30일 시작 예정 1건","모든 행사를 포함하지","숙박 수요나 매출 증가를 의미하지","한국관광공사"]) assert.ok(html.includes(text),text);
 assert.match(html,/<ul/);assert.match(html,/<time dateTime="2026-10-01"/);assert.match(html,/15101578/);
 assert.ok(html.indexOf("TEST ONGOING")<html.indexOf("TEST UPCOMING"));
});
test("event no-data states distinguish empty, unsynced, no region, coverage and errors",()=>{
 const data=fixture();data.events=[];data.total_count=0;
 assert.match(render(data),/선택한 기간에 확인된 공식 행사 정보가 없습니다/);
 data.available=false;data.reason="NOT_SYNCHRONIZED";
 assert.match(render(data),/행사 데이터가 아직 수집되지 않았습니다/);
 data.reason="PROPERTY_REGION_UNAVAILABLE";assert.match(render(data),/test\/edit/);
 data.reason="OUTSIDE_COLLECTED_WINDOW";assert.match(render(data),/선택한 기간의 행사 자료가 수집되지/);
 assert.match(render(null),/role="alert"/);
});
test("event truncation and summary have separate scopes",()=>{
 const data=fixture();data.events=data.events.slice(0,1);data.truncated=true;
 assert.match(render(data),/2건 중 1건/);assert.match(render(data),/향후 30일 시작 예정 1건/);
});

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";
import { runInNewContext } from "node:vm";
import { createElement, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";
import type { VisitorMarket } from "../src/lib/api/visitor-types.ts";
import * as transport from "../src/lib/api/transport.ts";

const require = createRequire(import.meta.url);
function load(path: string, dependencies: Record<string, unknown>) {
  const exports = {};
  runInNewContext(ts.transpileModule(readFileSync(new URL(path, import.meta.url), "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022 },
  }).outputText, { exports, process, URLSearchParams, require: (name: string) => dependencies[name] ?? require(name) });
  return exports;
}
const links = { default: ({ href, children }: { href: string; children: ReactNode }) => createElement("a", { href }, children) };

const views = load("../src/components/visitor-view.tsx", { "next/link": links,
 "./visitor-chart": { VisitorChart: ({ history }: { history: unknown[] }) => createElement("div", { "data-days": history.length }, "TEST CHART") },
}) as typeof import("../src/components/visitor-view");
// TEST ONLY synthetic API DTO, never production data.
function fixture(): VisitorMarket {
 return { property_id: "test-property", available: true, reason: null,
 scope: { level: "SIGUNGU", name: "부산광역시 수영구", source_region_code: "26500" },
 category: { code: "2", name: "외지인(b)" }, categories: [{ code: "1", name: "현지인(a)" }, { code: "2", name: "외지인(b)" }, { code: "3", name: "외국인(c)" }],
 latest: { date: "2026-08-31", value: "12345.67" }, rolling: { average_7d: "123.45", average_28d: "234.56", previous_7d_average: "100.00", change_7d_percent: "23.45" },
 history: Array.from({length: 90}, (_,i) => ({ date: new Date(Date.UTC(2026, 5, 3+i)).toISOString().slice(0,10), value: i === 1 ? null : "100.00" })),
 source: { source: "KTO_DATALAB_VISITORS_DAILY", provider: "한국관광공사", dataset: "한국관광공사_빅데이터_지역별 방문자수_GW", url: "https://www.data.go.kr/data/15101972/openapi.do", metric_label: "일별 추정 방문자", is_estimated: true, methodology: "이동통신 기반", methodology_version: null, last_collected_at: "2026-09-30T00:00:00Z", latest_reference_date: "2026-08-31", days_since_latest_reference: 30, latest_sync_status: "COMPLETED" },
 coverage: { requested_days: 90, available_days: 89, missing_days: 1, complete_7d: true, complete_28d: true, completeness: "APPLICATION_COVERAGE_ONLY" }, warnings: ["공식 데이터 제공 시차가 있을 수 있습니다."], calculation_version: "visitor-daily-v1", source_category: "public" };
}
const render = (data = fixture()) => renderToStaticMarkup(createElement(views.VisitorView,{data}));

test("visitor view renders separate categories, exact numbers, source and accessible 90-day table", () => {
 const html=render();
 for(const text of ["공식 지역 방문 추이", "외지인(b)", "외국인(c)", "현지인(a)", "12,345.67", "123.45", "234.56", "23.45%", "2026-08-31", "최근 90일", "자료 없음", "한국관광공사", "한국 시간", "숙박객 수, 예약 수", "30일 경과"]) assert.ok(html.includes(text),text);
 assert.match(html, /<label for="visitor-category"/); assert.match(html, /<table/);
 assert.match(html, /scope="col"/); assert.match(html, /value="2" selected/);
 assert.equal((html.match(/scope="row"/g)||[]).length,90);
 assert.doesNotMatch(html, /TOTAL|전월 대비|합산/);
});

test("missing windows, zero, not synced, no region and error remain distinct", () => {
 const data=fixture(); data.rolling.average_7d=null; data.rolling.average_28d=null;data.rolling.change_7d_percent=null;
 assert.match(render(data), /연속 7일·28일 자료가 없으면/);
 data.latest!.value="0"; assert.match(render(data), /0명/);
 data.available=false;data.reason="NOT_SYNCHRONIZED";
 assert.match(render(data), /방문자 데이터가 아직 수집되지 않았습니다/);assert.doesNotMatch(render(data), /TEST CHART/);
 data.reason="PROPERTY_REGION_UNAVAILABLE";data.scope=null;
 assert.ok(render(data).includes("test-property/edit"));
 assert.match(renderToStaticMarkup(createElement(views.VisitorView,{data:null,error:true})), /role="alert"/);
});

test("chart passes calendar gaps unchanged and explicitly disables interpolation", () => {
 let chartPoints: {value:number|null}[]=[]; let connects: unknown;
 const children=({children}:{children:ReactNode})=>createElement("div",null,children);
 const chart=load("../src/components/visitor-chart.tsx", {recharts: {
 ResponsiveContainer:children, LineChart:({data,children:child}:{data:typeof chartPoints;children:ReactNode})=>{chartPoints=data;return createElement("div",null,child);},
 CartesianGrid:()=>null,XAxis:()=>null,YAxis:()=>null,Tooltip:()=>null,
 Line:({connectNulls}:{connectNulls:boolean})=>{connects=connectNulls;return null;},
 }}) as typeof import("../src/components/visitor-chart");
 renderToStaticMarkup(createElement(chart.VisitorChart,{history:fixture().history}));
 assert.equal(chartPoints.length,90);assert.equal(chartPoints[1].value,null);assert.equal(connects,false);
});

test("market page sends selected category and preserves accommodation on visitor outage",async()=>{
 let fail=false; let selected="";
 const page=load("../src/app/(protected)/properties/[id]/market/page.tsx",{
 "@/lib/api/server":{requireOrganization:async()=>({organization_id:"org"}),serverApi:{eventMarket:async()=>null,accommodationMarket:async()=>({}),visitorMarket:async(org:string,id:string,cat:string)=>{assert.equal(org,"org");assert.equal(id,"test-property");selected=cat;if(fail)throw new transport.ApiError(503,"offline");return fixture();}}},
 "@/lib/api/transport":transport,"@/components/market-view":{MarketView:()=>createElement("p",null,"EXISTING ACCOMMODATION")},"@/components/event-view":{EventView:()=>null},"@/components/visitor-view":views,
 "next/navigation":{notFound:()=>{throw Error("NOT_FOUND");}},
 }) as {default:(p:{params:Promise<{id:string}>;searchParams:Promise<{category:string}>})=>Promise<ReactNode>};
 const props={params:Promise.resolve({id:"test-property"}),searchParams:Promise.resolve({category:"3"})};
 assert.match(renderToStaticMarkup(await page.default(props)),/공식 지역 방문 추이/);assert.equal(selected,"3");
 fail=true;const html=renderToStaticMarkup(await page.default(props));assert.match(html,/EXISTING ACCOMMODATION/);assert.match(html,/role="alert"/);
});

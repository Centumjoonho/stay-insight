import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";
import { runInNewContext } from "node:vm";
import { createElement, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";
import type { AccommodationMarket } from "../src/lib/api/market-types.ts";
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
const views = load("../src/components/market-view.tsx", { "next/link": links }) as typeof import("../src/components/market-view");
// DEVELOPMENT / TEST ONLY: synthetic API DTO, not an upstream file or actual market data.
function fixture(): AccommodationMarket {
  return {
    property_id: "test-property", region: { scope_level: "SIGUNGU", scope_name: "부산광역시 수영구", assignment_method: "EXPLICIT_SELECTION" },
    reference_date: "2026-09-28", window_start: "2025-09-29", window_end: "2026-09-28",
    market_context_available: true, reason: null,
    metrics: { open_businesses: 12, new_licenses_12m: 3, closures_12m: null,
      type_breakdown: { OTHER: 12 }, unknown_status_count: 1, missing_license_dates: 0, missing_closure_dates: 1 },
    freshness: { source: "MOIS_LODGINGS", source_dataset_name: "행정안전부_문화_숙박업",
      source_url: "https://www.data.go.kr/data/15044968/fileData.do", collected_at: "2026-09-28T00:00:00Z",
      source_reference_date: null, latest_sync_status: "COMPLETED", stale: false, stale_after_days: 7, live_provider_verified: false },
    warnings: [], source_category: "public", calculation_version: "license-market-v1",
  };
}
const render = (data = fixture()) => renderToStaticMarkup(createElement(views.MarketView, { data }));

test("market renders scope, counts, type, unavailable closures and official source/freshness", () => {
  const html = render();
  for (const text of ["지역 시장", "부산광역시 수영구", "구·군 단위", "12개", "3개", "데이터 없음", "기타 / 미분류",
    "행정안전부_문화_숙박업", "2026", "한국 시간", "실시간 자료가 아닙니다", "검증이 완료되지 않아"]) assert.ok(html.includes(text), text);
  assert.match(html, /https:\/\/www.data.go.kr\/data\/15044968\/fileData.do/);
  assert.match(html, /\/properties\/test-property\/dashboard/);
  assert.match(html, /\/properties\/test-property\/market/);
});

test("market unavailable region/sync hides numerical cards; confirmed zero remains visible", () => {
  const data = fixture();
  data.market_context_available = false; data.metrics = null; data.region = null;
  data.reason = "PROPERTY_REGION_UNAVAILABLE";
  assert.match(render(data), /지역 시장 정보를 보려면 숙소의 부산 구·군을 설정해 주세요/);
  assert.doesNotMatch(render(data), /0개|12개/);
  assert.ok(render(data).includes("/properties/test-property/edit"));
  data.reason = "NOT_SYNCHRONIZED";
  data.freshness.collected_at = null;
  assert.match(render(data), /아직 수집되지 않았거나/);
  assert.match(render(data), /수집 이력 없음/);
  const zero = fixture(); zero.metrics!.open_businesses = 0;
  assert.match(render(zero), /0개/);
});

test("market renders stale and failure warnings without fabricating values", () => {
  const data = fixture(); data.freshness.stale = true;
  data.warnings = ["최근 수집 실패 <script>" ];
  data.metrics!.new_licenses_12m = null;
  assert.match(render(data), /데이터 갱신이 필요합니다/);
  assert.match(render(data), /인허가일 누락/);
  assert.match(render(data), /&lt;script&gt;/);
  assert.doesNotMatch(render(data), /<script>/);
});

test("actual market page renders and propagates authorization/API errors; missing property is 404", async () => {
  let failure: unknown;
  const api = { accommodationMarket: async (org: string, id: string) => {
    assert.equal(org, "org"); assert.equal(id, "test-property");
    if (failure) throw failure; return fixture();
  }};
  const page = load("../src/app/(protected)/properties/[id]/market/page.tsx", {
    "@/lib/api/server": { requireOrganization: async () => ({ organization_id: "org" }), serverApi: api },
    "@/lib/api/transport": transport, "@/components/market-view": views,
    "next/navigation": { notFound: () => { throw Error("NOT_FOUND"); } },
  }) as { default: (props: { params: Promise<{ id: string }> }) => Promise<ReactNode> };
  const props = { params: Promise.resolve({ id: "test-property" }) };
  assert.match(renderToStaticMarkup(await page.default(props)), /지역 시장/);
  failure = new transport.ApiError(403, "forbidden");
  await assert.rejects(page.default(props), (error) => error === failure);
  failure = new Error("API unavailable");
  await assert.rejects(page.default(props), /API unavailable/);
  failure = new transport.ApiError(404, "not found");
  await assert.rejects(page.default(props), /NOT_FOUND/);
});

test("actual property navigation adds market and retains existing workflows", async () => {
  const page = load("../src/app/(protected)/properties/[id]/page.tsx", {
    "next/link": links, "next/navigation": { notFound: () => { throw Error("not found"); } },
    "@/lib/api/transport": transport,
    "@/lib/api/server": { requireOrganization: async () => ({ organization_id: "org" }),
      serverApi: { property: async () => ({ name: "TEST ONLY", address: "test", inventory_units: 1 }) } },
  }) as { default: (props: { params: Promise<{ id: string }> }) => Promise<ReactNode> };
  const html = renderToStaticMarkup(await page.default({ params: Promise.resolve({ id: "id" }) }));
  for (const label of ["지역 시장", "대시보드", "CSV 가져오기", "가져오기 기록", "예약 목록", "비용 관리"]) assert.ok(html.includes(label));
});

test("market server client forwards bearer/org, no-store, and redirects 401", async () => {
  let fail = false;
  const server = load("../src/lib/api/server.ts", {
    "@/lib/supabase/server": { serverAuth: async () => ({ auth: {
      getClaims: async () => ({ data: { claims: { sub: "test" } } }),
      getSession: async () => ({ data: { session: { access_token: "TEST_ONLY" } } }),
    } }) },
    "next/navigation": { redirect: () => { throw Error("LOGIN"); } },
    "./transport": { ...transport, apiRequest: async (_base: string, token: string, path: string, _init: unknown, org: string) => {
      assert.equal(token, "TEST_ONLY"); assert.equal(org, "org");
      assert.equal(path, "/api/v1/market/accommodations?property_id=id");
      if (fail) throw new transport.ApiError(401, "expired"); return fixture();
    } },
  }) as typeof import("../src/lib/api/server");
  assert.equal((await server.serverApi.accommodationMarket("org", "id")).source_category, "public");
  fail = true; await assert.rejects(server.serverApi.accommodationMarket("org", "id"), /LOGIN/);
});
test("market view follows new API region scope and retains source timestamp", () => {
  const data = fixture();
  const before = render(data);
  data.region!.scope_name = "부산광역시 해운대구";
  data.metrics!.open_businesses = 24;
  const after = render(data);
  assert.match(before, /부산광역시 수영구/);
  assert.match(after, /부산광역시 해운대구/);
  assert.match(after, /24개/);
  assert.doesNotMatch(after, /부산광역시 수영구/);
  assert.match(after, /행정안전부_문화_숙박업/);
});

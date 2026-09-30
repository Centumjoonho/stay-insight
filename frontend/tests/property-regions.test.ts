import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";
import { runInNewContext } from "node:vm";
import { JSDOM } from "jsdom";
import { act, createElement, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";
import type { PropertyCreate, PropertyResponse } from "../src/lib/api/types.ts";
import type { MarketRegion } from "../src/lib/api/region-types.ts";
import * as transport from "../src/lib/api/transport.ts";

const require = createRequire(import.meta.url);
function load(path: string, dependencies: Record<string, unknown>, globals = {}) {
  const exports = {};
  runInNewContext(ts.transpileModule(readFileSync(new URL(path, import.meta.url), "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022 },
  }).outputText, { exports, Error, process, URLSearchParams, ...globals, require: (name: string) => dependencies[name] ?? require(name) });
  return exports;
}
// Development/test fixtures only, never fallback data in the application.
const regions: MarketRegion[] = [
  { id: "suyeong", sido_name: "부산광역시", sigungu_name: "수영구", region_level: "SIGUNGU" },
  { id: "haeundae", sido_name: "부산광역시", sigungu_name: "해운대구", region_level: "SIGUNGU" },
];
const property: PropertyResponse = {
  id: "property", organization_id: "org", name: "개발 테스트", address: "테스트 주소", road_address: null,
  inventory_units: 1, accommodation_type: "HOTEL", timezone: "Asia/Seoul", created_at: "", updated_at: "",
  region_id: "suyeong", region: regions[0],
};

test("property form loads regions, creates, edits, preserves current choice, clears and refreshes", async (t) => {
  const dom = new JSDOM("<!doctype html><div id='root'></div>", { url: "http://localhost:3000" });
  const previous = new Map<string, PropertyDescriptor | undefined>();
  for (const [name, value] of Object.entries({ window: dom.window, document: dom.window.document,
    HTMLElement: dom.window.HTMLElement, IS_REACT_ACT_ENVIRONMENT: true })) {
    previous.set(name, Object.getOwnPropertyDescriptor(globalThis, name));
    Object.defineProperty(globalThis, name, { configurable: true, writable: true, value });
  }
  const { createRoot } = await import("react-dom/client");
  const root = createRoot(dom.window.document.getElementById("root")!);
  t.after(async () => {
    await act(async () => root.unmount()); dom.window.close();
    for (const [name, descriptor] of previous) {
      if (descriptor) Object.defineProperty(globalThis, name, descriptor); else Reflect.deleteProperty(globalThis, name);
    }
  });
  let resolveRegions: (items: MarketRegion[]) => void = () => {};
  let lookup = () => new Promise<MarketRegion[]>((resolve) => { resolveRegions = resolve; });
  let saved: PropertyCreate | undefined, updates = 0, refreshes = 0, destination = "", failure = false;
  const form = load("../src/components/property-form.tsx", {
    "@/lib/api/client": { businessApi: {
      regions: () => lookup(),
      createProperty: async (org: string, body: PropertyCreate) => { assert.equal(org, "org"); saved = body; return property; },
      updateProperty: async (org: string, id: string, body: PropertyCreate) => {
        assert.equal(org, "org"); assert.equal(id, "property");
        if (failure) throw new Error("입력 내용을 확인해 주세요.");
        saved = body; updates++; return property;
      },
    } },
    "next/navigation": { useRouter: () => ({ replace: (url: string) => { destination = url; }, refresh: () => { refreshes++; } }) },
  }, { FormData: dom.window.FormData }) as typeof import("../src/components/property-form");
  const doc = dom.window.document;
  const select = () => doc.querySelector<HTMLSelectElement>('[name="region_id"]')!;
  const submit = () => act(async () => { doc.querySelector("form")!.dispatchEvent(new dom.window.Event("submit", { bubbles: true, cancelable: true })); });
  const choose = (value: string) => act(async () => {
    select().value = value; select().dispatchEvent(new dom.window.Event("change", { bubbles: true }));
  });
  await act(async () => root.render(createElement(form.PropertyForm, { organizationId: "org" })));
  assert.equal(select().disabled, true); assert.match(doc.body.textContent!, /불러오는 중/);
  await submit(); assert.equal(saved, undefined);
  await act(async () => resolveRegions(regions));
  assert.equal(select().options.length, 3); assert.equal(select().value, "");
  await choose("suyeong");
  doc.querySelector<HTMLInputElement>('[name="name"]')!.value = "개발 테스트";
  doc.querySelector<HTMLInputElement>('[name="address"]')!.value = "테스트 주소";
  await submit(); assert.equal(saved!.region_id, "suyeong");
  assert.equal(destination, "/properties/property"); assert.equal(refreshes, 1);
  lookup = async () => regions;
  await act(async () => root.render(createElement(form.PropertyForm, { key: "edit", organizationId: "org", property })));
  assert.equal(select().value, "suyeong"); assert.equal(doc.querySelector<HTMLInputElement>('[name="address"]')!.value, property.address);
  await choose("haeundae"); failure = true; await submit();
  assert.equal(updates, 0); assert.match(doc.querySelector('[role="alert"]')!.textContent!, /입력 내용/);
  failure = false; await submit(); assert.equal(saved!.region_id, "haeundae"); assert.equal(updates, 1);
  assert.equal(saved!.address, property.address); assert.equal(refreshes, 2);
  await act(async () => root.render(createElement(form.PropertyForm, { key: "clear", organizationId: "org", property })));
  await choose(""); await submit(); assert.equal(saved!.region_id, null);
  lookup = async () => { throw new Error("offline"); };
  await act(async () => root.render(createElement(form.PropertyForm, { key: "error", organizationId: "org", property })));
  assert.equal(select().value, "suyeong"); assert.equal(select().disabled, true);
  assert.match(doc.body.textContent!, /불러올 수 없습니다/);
  lookup = async () => regions;
  await act(async () => [...doc.querySelectorAll("button")].find((b) => b.textContent === "다시 시도")!.click());
  assert.equal(select().value, "suyeong"); assert.equal(select().disabled, false);
  lookup = async () => [];
  await act(async () => root.render(createElement(form.PropertyForm, { key: "empty", organizationId: "org" })));
  assert.match(doc.body.textContent!, /선택 가능한 부산 지역 정보가 없습니다/);
  assert.equal(select().value, "");
  await act(async () => root.render(createElement(form.PropertyForm, { key: "invalid", organizationId: "org", property })));
  await submit(); assert.match(doc.querySelector('[role="alert"]')!.textContent!, /선택 가능한 부산 구·군/);
});

test("property detail and edit render current region, missing region, and propagate authorization", async () => {
  let item = property, failure: unknown;
  const dependencies = {
    "next/link": { default: ({ href, children }: { href: string; children: ReactNode }) => createElement("a", { href }, children) },
    "next/navigation": { notFound: () => { throw Error("NOT_FOUND"); } },
    "@/lib/api/transport": transport,
    "@/lib/api/server": { requireOrganization: async () => ({ organization_id: "org" }), serverApi: {
      property: async (org: string, id: string) => { assert.equal(org, "org"); assert.equal(id, "property"); if (failure) throw failure; return item; },
    } },
    "@/components/property-form": { PropertyForm: ({ property: p }: { property: PropertyResponse }) => createElement("p", null, p.region?.sigungu_name ?? "미설정") },
  };
  type Page = { default: (p: { params: Promise<{ id: string }> }) => Promise<ReactNode> };
  const detail = load("../src/app/(protected)/properties/[id]/page.tsx", dependencies) as Page;
  const edit = load("../src/app/(protected)/properties/[id]/edit/page.tsx", dependencies) as Page;
  const props = { params: Promise.resolve({ id: "property" }) };
  const html = renderToStaticMarkup(await detail.default(props));
  assert.match(html, /부산광역시 수영구/); assert.ok(html.includes("/properties/property/edit"));
  assert.match(renderToStaticMarkup(await edit.default(props)), /수영구/);
  item = { ...property, region: regions[1], region_id: "haeundae" };
  assert.match(renderToStaticMarkup(await detail.default(props)), /해운대구/);
  item = { ...property, region: null, region_id: null };
  assert.match(renderToStaticMarkup(await detail.default(props)), /미설정/);
  failure = new transport.ApiError(404, "missing"); await assert.rejects(edit.default(props), /NOT_FOUND/);
  failure = new transport.ApiError(403, "forbidden"); await assert.rejects(edit.default(props), (e) => e === failure);
});

test("central client sends region selection to versioned authenticated API", async () => {
  const calls: { path: string; body?: string; org?: string }[] = [];
  const client = load("../src/lib/api/client.ts", {
    "@/lib/imports": {}, "@/lib/supabase/client": { browserAuth: () => ({ auth: {
      getSession: async () => ({ data: { session: { access_token: "TEST_ONLY" } } }),
    } }) },
    "./transport": { ...transport, apiRequest: async (_base: unknown, token: string, path: string, init?: RequestInit, org?: string) => {
      assert.equal(token, "TEST_ONLY"); calls.push({ path, body: init?.body as string, org }); return property;
    } },
  }) as typeof import("../src/lib/api/client");
  await client.businessApi.regions();
  const query = new URLSearchParams(calls[0].path.split("?")[1]);
  assert.equal(query.get("sido"), "부산광역시"); assert.equal(query.get("level"), "SIGUNGU");
  await client.businessApi.createProperty("org", { ...property, region_id: "suyeong" });
  await client.businessApi.updateProperty("org", "property", { region_id: "haeundae" });
  assert.equal(calls[1].org, "org"); assert.equal(JSON.parse(calls[1].body!).region_id, "suyeong");
  assert.equal(calls[2].path, "/api/v1/properties/property"); assert.equal(calls[2].org, "org");
  assert.equal(JSON.parse(calls[2].body!).region_id, "haeundae");
});

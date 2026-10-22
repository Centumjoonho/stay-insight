import assert from "node:assert/strict";
import test from "node:test";
import { createElement, type AnchorHTMLAttributes } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { JSDOM } from "jsdom";
import { compile, sharedUi, sharedPropertyNav } from "./shared-ui.ts";
import type { Reservation } from "../src/lib/api/import-types.ts";

const links = { default: ({ href, ...props }: AnchorHTMLAttributes<HTMLAnchorElement>) => createElement("a", { ...props, href }) };
test("property navigation exposes existing routes and identifies the current destination", () => {
  const dom = new JSDOM(renderToStaticMarkup(createElement(sharedPropertyNav.PropertyNav, { id: "property", active: "예약 목록" })));
  const current = dom.window.document.querySelectorAll('[aria-current="page"]');
  assert.equal(current.length, 1);
  assert.equal(current[0].getAttribute("href"), "/properties/property/reservations");
  for (const suffix of ["", "/dashboard", "/expenses", "/inventory", "/market", "/imports/new", "/imports"]) assert.ok(dom.window.document.querySelector(`a[href="/properties/property${suffix}"]`));
  dom.window.close();
});
test("mobile reservation card keeps exact money, unknown quantities, status and safe identity", () => {
  const { ReservationMobileCard } = compile("../src/components/reservation-table.tsx", { "next/link": links, "@/components/ui": sharedUi }) as typeof import("../src/components/reservation-table");
  const row: Reservation = { id: "r", property_id: "p", origin: "MANUAL", version: 1, import_id: null, external_reservation_id: "<script>name</script>", manual_protected_fields: [], channel: "DIRECT", check_in: "2026-09-01", check_out: "2026-09-03", booked_nights: 2, guest_count: null, room_units: null, gross_revenue: "9007199254740993", channel_fee: "0", net_revenue: "9007199254740993", reservation_status: "CANCELLED" };
  const html = renderToStaticMarkup(createElement(ReservationMobileCard, { item: row }));
  assert.ok(html.includes("9,007,199,254,740,993원"));
  assert.ok(html.includes("수수료 0원"));
  assert.ok(html.includes("객실 미입력") && html.includes("투숙인원 미입력"));
  assert.ok(html.includes("수동 등록") && html.includes("취소"));
  assert.ok(html.includes('href="/properties/p/reservations/r"'));
  assert.ok(!html.includes("<script>") && !html.includes("수동 보정"));
});
test("KPI presentation labels estimates and unavailable comparisons without inventing data", () => {
  const html = renderToStaticMarkup(createElement(sharedUi.KpiCard, { label: "RevPAR", value: "계산 불가", estimated: true, comparison: "전월 대비 비교 데이터 없음", yearComparison: "전년 동월 비교 데이터 없음" }));
  assert.ok(html.includes("추정") && html.includes("계산 불가"));
  assert.ok(!html.includes("0원") && !html.includes("실제 점유율"));
  const dom = new JSDOM(html);
  assert.equal(dom.window.document.querySelector("article h2")?.textContent, "RevPAR추정");
  dom.window.close();
});
test("properties screen preserves scoped API results, registration and property navigation", async () => {
  const property = { id: "p", name: "숙소 <이름>", address: "입력 주소 <script>unsafe</script>", inventory_units: 6 };
  const page = compile("../src/app/(protected)/properties/page.tsx", { "next/link": links, "@/components/ui": sharedUi, "@/lib/api/server": { requireOrganization: async () => ({ organization_id: "org", organization_name: "입력 조직" }), serverApi: { properties: async (org: string, offset: number) => { assert.equal(org, "org"); assert.equal(offset, 0); return { total: 1, items: [property] }; } } } }) as typeof import("../src/app/(protected)/properties/page");
  const html = renderToStaticMarkup(await page.default({ searchParams: Promise.resolve({}) }));
  assert.ok(html.includes("입력 조직") && html.includes("6실"));
  assert.ok(html.includes('href="/properties/new"') && html.includes('href="/properties/p"'));
  assert.ok(!html.includes("<script>") && !html.includes("centumoffice"));
});

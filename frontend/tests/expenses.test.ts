import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";
import { runInNewContext } from "node:vm";
import { createElement, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";
import * as contracts from "../src/lib/api/expense-types.ts";
import type { Expense, ExpenseSummary } from "../src/lib/api/expense-types.ts";
import * as helpers from "../src/lib/expenses.ts";
import * as transport from "../src/lib/api/transport.ts";

const require = createRequire(import.meta.url);
function load(path: string, dependencies: Record<string, unknown>) {
  const exports = {};
  runInNewContext(ts.transpileModule(readFileSync(new URL(path, import.meta.url), "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022 },
  }).outputText, { exports, process, FormData, require: (name: string) => dependencies[name] ?? require(name) });
  return exports;
}
const item: Expense = {
  id: "e1", organization_id: "org", property_id: "property", source: "MANUAL",
  expense_date: "2026-09-01", category: "RENT", cost_type: "FIXED", amount: "9007199254740993",
  memo: "<script>fixture</script>", created_by_user_id: "user", created_at: "", updated_at: "",
};

test("expense validation requires explicit categories/types and exact nonnegative integer KRW", () => {
  const form = new FormData();
  for (const [key, value] of Object.entries(item)) form.set(key, value);
  assert.equal(helpers.expenseFormValues(form).amount, "9007199254740993");
  for (const [key, value] of [
    ["cost_type", ""], ["category", "OTA_FEE"], ["amount", "-1"], ["amount", "0.5"],
    ["amount", "1e6"], ["amount", "1000000000000000000"], ["expense_date", "2026-02-30"],
  ]) {
    const previous = form.get(key)!; form.set(key, value);
    assert.throws(() => helpers.expenseFormValues(form)); form.set(key, previous);
  }
  form.set("amount", "0"); assert.equal(helpers.expenseFormValues(form).amount, "0");
});

test("month defaults use Seoul and filters/pagination preserve explicit dates without shifting", () => {
  assert.deepEqual(helpers.seoulPeriod(new Date("2026-12-31T15:00:00Z")), {
    from: "2027-01-01", to: "2027-01-31", today: "2027-01-01",
  });
  assert.equal(helpers.seoulPeriod(new Date("2028-02-15T00:00:00Z")).to, "2028-02-29");
  const q = helpers.expenseQuery("p", { from: "2026-09-01", to: "2026-09-30", category: "RENT", cost_type: "FIXED", offset: "50" });
  assert.equal(q.list.get("offset"), "50"); assert.equal(q.list.get("category"), "RENT");
  assert.equal(q.list.get("cost_type"), "FIXED"); assert.equal(q.period.has("cost_type"), false);
  assert.equal(q.period.get("from"), "2026-09-01");
  assert.throws(() => helpers.expenseQuery("p", { from: "2026-10-01", to: "2026-09-01" }));
  assert.throws(() => helpers.expenseQuery("p", { offset: "-1" }));
  assert.equal(helpers.won("9007199254740993"), "9,007,199,254,740,993원");
});

test("expense list escapes memo and summary keeps channel fees read-only with coverage", () => {
  const views = load("../src/components/expense-views.tsx", {
    "@/lib/api/expense-types": contracts, "@/lib/expenses": helpers,
    "./expense-delete": { ExpenseDelete: () => createElement("button", null, "삭제") },
    "next/link": { default: ({ href, children }: { href: string; children: ReactNode }) => createElement("a", { href }, children) },
  }) as typeof import("../src/components/expense-views.tsx");
  const list = renderToStaticMarkup(createElement(views.ExpenseTable, {
    items: [item], organizationId: "org", propertyId: "property",
  }));
  assert.ok(list.includes("&lt;script&gt;")); assert.ok(!list.includes("<script>"));
  assert.ok(list.includes("/properties/property/expenses/e1/edit"));
  assert.ok(list.includes("9,007,199,254,740,993원"));
  const summary: ExpenseSummary = {
    property_id: "property", from_date: "2026-09-01", to_date: "2026-09-30",
    manual_expense_total: "1750000", fixed_expense_total: "1450000", variable_expense_total: "300000",
    channel_fee_total: "50", known_cost_total: "1750050",
    category_breakdown: [{ category: "RENT", amount: "1200000" }],
    cost_type_breakdown: [{ cost_type: "FIXED", amount: "1450000" }, { cost_type: "VARIABLE", amount: "300000" }],
    reservations_with_fee: 2, reservations_missing_fee: 1, manual_source: "MANUAL",
    channel_fee_source: "owner_csv", channel_fee_date_basis: "check_in", is_estimated: false,
  };
  const html = renderToStaticMarkup(createElement(views.ExpenseSummaryView, { summary }));
  assert.ok(html.includes("1,750,050원")); assert.ok(html.includes("읽기 전용"));
  assert.ok(html.includes("수수료 미입력 예약 1건")); assert.ok(html.includes("체크인일"));
  assert.ok(!/<(input|button|select)/.test(html));
});

test("central expense client creates/edits/deletes with bearer and tenant context and safe 401/403 errors", async (t) => {
  const api = load("../src/lib/api/client.ts", {
    "@/lib/supabase/client": { browserAuth: () => ({ auth: { getSession: async () => ({
      data: { session: { access_token: "test-only-token" } }, error: null,
    }) } }) },
    "@/lib/imports": {}, "./transport": transport,
  }) as typeof import("../src/lib/api/client.ts");
  t.mock.method(globalThis, "fetch", async (_url: string | URL | Request, options?: RequestInit) => {
    const headers = new Headers(options?.headers);
    assert.equal(headers.get("Authorization"), "Bearer test-only-token");
    assert.equal(headers.get("X-Organization-Id"), "org");
    assert.equal(options?.cache, "no-store");
    if (options?.method === "DELETE") return new Response(null, { status: 204 });
    const body = JSON.parse(options?.body as string);
    assert.equal(body.amount, "9007199254740993");
    return Response.json(item, { status: options?.method === "POST" ? 201 : 200 });
  });
  const old = process.env.NEXT_PUBLIC_API_BASE_URL;
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8000";
  t.after(() => { if (old === undefined) delete process.env.NEXT_PUBLIC_API_BASE_URL; else process.env.NEXT_PUBLIC_API_BASE_URL = old; });
  const values = { expense_date: item.expense_date, category: item.category, cost_type: item.cost_type, amount: item.amount, memo: item.memo };
  assert.equal((await api.businessApi.createExpense("org", { ...values, property_id: "property" })).id, "e1");
  assert.equal((await api.businessApi.updateExpense("org", "e1", values)).amount, item.amount);
  assert.equal(await api.businessApi.deleteExpense("org", "e1"), undefined);
  for (const status of [401, 403]) await assert.rejects(
    transport.apiRequest("http://localhost:8000", "token", "/api/v1/expenses/e1",
      { method: "DELETE" }, "org", async () => new Response("private database details", { status })),
    (error: unknown) => error instanceof transport.ApiError && error.status === status && !error.message.includes("database"),
  );
});

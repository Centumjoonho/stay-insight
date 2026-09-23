import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";
import { runInNewContext } from "node:vm";
import { JSDOM } from "jsdom";
import { act, createElement, type ReactNode } from "react";
import ts from "typescript";
import * as contracts from "../src/lib/api/expense-types.ts";
import * as helpers from "../src/lib/expenses.ts";

test("actual expense form creates/edits and deletion requires confirmation then refreshes", async (t) => {
  const dom = new JSDOM("<!doctype html><div id='root'></div>", { url: "http://localhost:3000" });
  const previous = new Map<string, PropertyDescriptor | undefined>();
  for (const [name, value] of Object.entries({
    window: dom.window, document: dom.window.document, HTMLElement: dom.window.HTMLElement, IS_REACT_ACT_ENVIRONMENT: true,
  })) {
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
  let creates = 0, updates = 0, deletes = 0, refreshes = 0, destination = "", fail = false;
  const item: contracts.Expense = {
    id: "expense", property_id: "property", organization_id: "org", expense_date: "2026-09-01",
    category: "RENT", cost_type: "FIXED", amount: "1200000", memo: null, source: "MANUAL",
    created_at: "", updated_at: "", created_by_user_id: "user",
  };
  const api = {
    createExpense: async (org: string, body: contracts.ExpenseValues & { property_id: string }) => {
      assert.equal(org, "org"); assert.equal(body.property_id, "property");
      assert.equal(body.amount, "1200000"); assert.equal(body.cost_type, "FIXED"); creates++; return item;
    },
    updateExpense: async (org: string, id: string, body: contracts.ExpenseValues) => {
      assert.equal(org, "org"); assert.equal(id, "expense"); assert.equal(body.amount, "300000");
      updates++; return item;
    },
    deleteExpense: async () => { if (fail) throw new Error("이 사업장에 접근할 권한이 없습니다."); deletes++; },
  };
  const require = createRequire(import.meta.url);
  function load(path: string) {
    const exports = {};
    const dependencies: Record<string, unknown> = {
      "@/lib/api/expense-types": contracts, "@/lib/expenses": helpers, "@/lib/api/client": { businessApi: api },
      "next/navigation": { useRouter: () => ({ replace: (url: string) => { destination = url; }, refresh: () => { refreshes++; } }) },
      "next/link": { default: ({ href, children }: { href: string; children: ReactNode }) => createElement("a", { href }, children) },
    };
    runInNewContext(ts.transpileModule(readFileSync(new URL(path, import.meta.url), "utf8"), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022 },
    }).outputText, { exports, Error, FormData: dom.window.FormData, require: (name: string) => dependencies[name] ?? require(name) });
    return exports;
  }
  const { ExpenseForm } = load("../src/components/expense-form.tsx") as typeof import("../src/components/expense-form.tsx");
  const { ExpenseDelete } = load("../src/components/expense-delete.tsx") as typeof import("../src/components/expense-delete.tsx");
  const doc = dom.window.document;
  const button = (name: string) => {
    const result = [...doc.querySelectorAll("button")].find((node) => node.textContent === name);
    assert.ok(result, name); return result;
  };
  await act(async () => root.render(createElement(ExpenseForm, { propertyId: "property", organizationId: "org", today: "2026-09-01" })));
  assert.equal(doc.querySelector<HTMLSelectElement>('[name="cost_type"]')!.value, "");
  const submit = async () => act(async () => { doc.querySelector("form")!.dispatchEvent(new dom.window.Event("submit", { bubbles: true, cancelable: true })); });
  await submit(); assert.equal(creates, 0); assert.ok(doc.querySelector('[role="alert"]')?.textContent);
  for (const [key, value] of Object.entries({ category: "RENT", cost_type: "FIXED", amount: "1200000" })) {
    (doc.querySelector(`[name="${key}"]`) as HTMLInputElement).value = value;
  }
  await submit(); assert.equal(creates, 1); assert.equal(refreshes, 1);
  assert.equal(destination, "/properties/property/expenses?from=2026-09-01&to=2026-09-01");
  await act(async () => root.render(createElement(ExpenseForm, { key: "edit", propertyId: "property", organizationId: "org", today: "2026-09-01", expense: item })));
  doc.querySelector<HTMLInputElement>('[name="amount"]')!.value = "300000";
  await submit(); assert.equal(updates, 1); assert.equal(refreshes, 2);
  await act(async () => root.render(createElement(ExpenseDelete, { organizationId: "org", expenseId: "expense" })));
  await act(async () => button("삭제").click()); assert.equal(deletes, 0);
  await act(async () => button("취소").click()); assert.equal(deletes, 0);
  await act(async () => button("삭제").click()); fail = true;
  await act(async () => button("삭제 확인").click());
  assert.equal(deletes, 0); assert.equal(refreshes, 2); assert.ok(doc.querySelector('[role="alert"]')?.textContent?.includes("권한"));
  fail = false; await act(async () => button("삭제 확인").click());
  assert.equal(deletes, 1); assert.equal(refreshes, 3);
});

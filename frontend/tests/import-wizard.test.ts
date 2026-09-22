import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";
import { runInNewContext } from "node:vm";
import { JSDOM } from "jsdom";
import { act, createElement, type ReactNode } from "react";
import ts from "typescript";
import { channels } from "../src/lib/api/import-types.ts";
import * as imports from "../src/lib/imports.ts";

test("wizard requires explicit mapping and confirmation, imports, and invalidates stale validation", async (t) => {
  const dom = new JSDOM("<!doctype html><html><body><div id='root'></div></body></html>", { url: "http://localhost:3000" });
  const previous = new Map<string, PropertyDescriptor | undefined>();
  for (const [name, value] of Object.entries({
    window: dom.window, document: dom.window.document, HTMLElement: dom.window.HTMLElement,
    IS_REACT_ACT_ENVIRONMENT: true,
  })) {
    previous.set(name, Object.getOwnPropertyDescriptor(globalThis, name));
    Object.defineProperty(globalThis, name, { configurable: true, writable: true, value });
  }
  const { createRoot } = await import("react-dom/client");
  const root = createRoot(dom.window.document.getElementById("root")!);
  t.after(async () => {
    await act(async () => root.unmount());
    dom.window.close();
    for (const [name, descriptor] of previous) {
      if (descriptor) Object.defineProperty(globalThis, name, descriptor);
      else Reflect.deleteProperty(globalThis, name);
    }
  });
  let previewCalls = 0, validationCalls = 0, importCalls = 0;
  const headers = ["ID", "IN", "OUT", "GROSS"];
  const businessApi = {
    previewCsv: async (file: File) => {
      assert.equal(file.name, "development-only.csv"); previewCalls++;
      return { encoding: "utf-8", headers, rows: [["R1", "2026-09-01", "2026-09-03", "100000"]], total_rows: 1, warnings: [] };
    },
    validateImport: async (org: string, property: string, channel: string, mapping: unknown) => {
      assert.equal(org, "org"); assert.equal(property, "property"); assert.equal(channel, "GENERIC");
      assert.equal(JSON.stringify(mapping), JSON.stringify({
        external_reservation_id: "ID", check_in: "IN", check_out: "OUT", gross_revenue: "GROSS",
      }));
      validationCalls++;
      return { total_rows: 1, valid_rows: 1, invalid_rows: 0, errors: [], errors_truncated: false, warnings: [] };
    },
    importCsv: async () => {
      importCalls++;
      return { status: "COMPLETED", total_rows: 1, imported_rows: 1, rejected_rows: 0,
        inserted_rows: 1, updated_rows: 0, duplicate: false, validation_errors: [], error_message: null };
    },
  };
  const require = createRequire(import.meta.url);
  function load(path: string, dependencies: Record<string, unknown>) {
    const source = readFileSync(new URL(path, import.meta.url), "utf8");
    const exports = {};
    runInNewContext(ts.transpileModule(source, {
      compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022 },
    }).outputText, { exports, require: (name: string) => dependencies[name] ?? require(name) });
    return exports;
  }
  const views = load("../src/components/import-views.tsx", { "@/lib/imports": imports });
  const { ImportWizard } = load("../src/components/import-wizard.tsx", {
    "@/lib/imports": imports, "./import-views": views, "@/lib/api/client": { businessApi },
    "@/lib/api/import-types": { channels },
    "next/link": { default: ({ href, children }: { href: string; children: ReactNode }) => createElement("a", { href }, children) },
  }) as typeof import("../src/components/import-wizard.tsx");
  await act(async () => root.render(createElement(ImportWizard, { propertyId: "property", organizationId: "org" })));
  const document = dom.window.document;
  const button = (text: string) => {
    const result = [...document.querySelectorAll("button")].find((node) => node.textContent === text);
    assert.ok(result, text); return result;
  };
  assert.ok(button("미리보기").disabled);
  const input = document.querySelector<HTMLInputElement>('input[type="file"]')!;
  Object.defineProperty(input, "files", { configurable: true, value: [new File(["fixture"], "development-only.csv")] });
  await act(async () => input.dispatchEvent(new dom.window.Event("change", { bubbles: true })));
  await act(async () => button("미리보기").click());
  assert.equal(previewCalls, 1);
  assert.equal(document.querySelectorAll("tbody td").length, 4);
  assert.ok(button("검증하기").disabled);
  const selects = [...document.querySelectorAll("fieldset")][1].querySelectorAll("select");
  for (let i = 0; i < headers.length; i++) {
    await act(async () => {
      selects[i].value = headers[i];
      selects[i].dispatchEvent(new dom.window.Event("change", { bubbles: true }));
    });
  }
  assert.equal(button("검증하기").disabled, false);
  await act(async () => button("검증하기").click());
  assert.equal(validationCalls, 1);
  assert.ok(button("5. 가져오기").disabled);
  await act(async () => document.querySelector<HTMLInputElement>('input[type="checkbox"]')!.click());
  assert.equal(button("5. 가져오기").disabled, false);
  await act(async () => button("5. 가져오기").click());
  assert.equal(importCalls, 1);
  assert.ok(document.querySelector('[aria-label="가져오기 결과"]')?.textContent?.includes("가져오기 완료"));
  assert.ok(button("5. 가져오기").disabled);
  await act(async () => {
    selects[0].value = "";
    selects[0].dispatchEvent(new dom.window.Event("change", { bubbles: true }));
  });
  assert.equal(document.querySelector('[aria-label="검증 결과"]'), null);
  assert.equal(document.querySelector('[aria-label="가져오기 결과"]'), null);
  assert.ok(button("검증하기").disabled);
});

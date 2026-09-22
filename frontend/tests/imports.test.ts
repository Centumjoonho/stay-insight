import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";
import { runInNewContext } from "node:vm";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";
import { importForm, mappingErrors, mappingFields } from "../src/lib/imports.ts";
import { apiRequest, ApiError } from "../src/lib/api/transport.ts";
import type { ImportResult } from "../src/lib/api/import-types.ts";

const headers = ["예약번호", "체크인", "체크아웃", "금액"];
const mapping = { external_reservation_id: "예약번호", check_in: "체크인", check_out: "체크아웃", gross_revenue: "금액" };
const require = createRequire(import.meta.url);
const source = readFileSync(new URL("../src/components/import-views.tsx", import.meta.url), "utf8");
const exports = {};
runInNewContext(ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022 },
}).outputText, {
  exports,
  require: (name: string) => name === "@/lib/imports" ? { mappingFields } : require(name),
});
const views = exports as typeof import("../src/components/import-views.tsx");

test("CSV preview renders data as text, including HTML and formulas", () => {
  const html = renderToStaticMarkup(createElement(views.CsvPreviewTable, { preview: {
    encoding: "utf-8", headers, rows: [["<script>alert(1)</script>", "=1+1", "2026-09-03", "100"]],
    total_rows: 1, warnings: [],
  } }));
  assert.equal((html.match(/<th /g) ?? []).length, 4);
  assert.equal((html.match(/<td /g) ?? []).length, 4);
  assert.ok(html.includes("&lt;script&gt;"));
  assert.ok(!html.includes("<script>"));
  assert.ok(html.includes("=1+1"));
});

test("mapping requires explicit distinct existing columns", () => {
  assert.equal(mappingErrors({}, headers).length, 4);
  assert.deepEqual(mappingErrors(mapping, headers), []);
  assert.ok(mappingErrors({ ...mapping, check_out: "체크인" }, headers).length > 0);
  assert.ok(mappingErrors({ ...mapping, gross_revenue: "missing" }, headers).length > 0);
  const html = renderToStaticMarkup(createElement(views.MappingFields, {
    headers, mapping: {}, onChange: () => {}, disabled: true,
  }));
  assert.equal((html.match(/<select /g) ?? []).length, 7);
  assert.equal((html.match(/ required=""/g) ?? []).length, 4);
  assert.ok(html.includes("<fieldset disabled="));
  assert.ok(!html.includes('value="예약번호" selected'));
});

test("validation shows errors without presenting partial import as success", () => {
  const html = renderToStaticMarkup(createElement(views.ValidationSummary, { result: {
    total_rows: 2, valid_rows: 1, invalid_rows: 1, errors_truncated: false, warnings: [],
    errors: [{ row: 3, field: "check_out", message: "날짜 오류" }],
  } }));
  assert.ok(html.includes("3행 / check_out"));
  assert.ok(html.includes("일부 행만 가져오지 않습니다."));
});

test("import result distinguishes failed, completed and duplicate batches", () => {
  const batch: ImportResult = { id: "test", property_id: "p", channel: "GENERIC", original_filename: "fixture.csv",
    status: "FAILED", total_rows: 2, imported_rows: 0, rejected_rows: 1, inserted_rows: 0, updated_rows: 0,
    created_at: "", error_message: "검증 실패", validation_errors: [], duplicate: false };
  const failed = renderToStaticMarkup(createElement(views.ImportResultView, { result: batch }));
  assert.ok(failed.includes("가져오기 실패"));
  assert.ok(failed.includes("예약 변경은 저장되지 않았습니다."));
  assert.ok(failed.includes('role="alert"'));
  const complete = renderToStaticMarkup(createElement(views.ImportResultView, {
    result: { ...batch, status: "COMPLETED", imported_rows: 2, rejected_rows: 0, inserted_rows: 1,
      updated_rows: 1, duplicate: true, error_message: null },
  }));
  assert.ok(complete.includes("가져오기 완료"));
  assert.ok(complete.includes("이미 가져온 파일"));
  assert.ok(!complete.includes('role="alert"'));
});

test("multipart import preserves file, mapping, auth and organization without a JSON content type", async () => {
  const file = new File(["id,in,out,gross\n1,2026-09-01,2026-09-02,100\n"], "fixture.csv", { type: "text/csv" });
  const body = importForm(file, "property", "GENERIC", mapping);
  const fake: typeof fetch = async (url, options) => {
    assert.equal(url, "https://api.example.test/api/v1/imports");
    const sent = new Headers(options?.headers);
    assert.equal(sent.get("Authorization"), "Bearer token");
    assert.equal(sent.get("X-Organization-Id"), "org");
    assert.equal(sent.has("Content-Type"), false);
    assert.equal(options?.body, body);
    assert.equal(body.get("property_id"), "property");
    assert.deepEqual(JSON.parse(body.get("column_mapping") as string), mapping);
    assert.equal((body.get("file") as File).name, "fixture.csv");
    assert.equal(options?.cache, "no-store");
    return Response.json({ status: "COMPLETED" });
  };
  assert.deepEqual(await apiRequest("https://api.example.test", "token", "/api/v1/imports",
    { method: "POST", body }, "org", fake), { status: "COMPLETED" });
});

test("import auth and upload errors do not expose raw server data", async () => {
  for (const status of [401, 403, 413, 422, 500]) {
    await assert.rejects(apiRequest("https://api.example.test", "token", "/api/v1/imports",
      { method: "POST", body: new FormData() }, "org",
      async () => new Response("private raw row", { status })),
    (error: unknown) => error instanceof ApiError && error.status === status && !error.message.includes("raw row"));
  }
});

import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { runInNewContext } from "node:vm";
import { createElement, type AnchorHTMLAttributes } from "react";
import ts from "typescript";

const require = createRequire(import.meta.url);
const links = { default: ({ href, ...props }: AnchorHTMLAttributes<HTMLAnchorElement>) => createElement("a", { ...props, href }) };
export function compile(path: string, dependencies: Record<string, unknown> = {}) {
  const exports = {};
  runInNewContext(ts.transpileModule(readFileSync(new URL(path, import.meta.url), "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022 },
  }).outputText, { exports, require: (name: string) => dependencies[name] ?? require(name) });
  return exports;
}
// Render real shared UI in the existing TSX test harness; no layout/business stubs.
export const sharedUi = compile("../src/components/ui.tsx") as typeof import("../src/components/ui");
export const sharedPropertyNav = compile("../src/components/property-nav.tsx", { "next/link": links }) as typeof import("../src/components/property-nav");

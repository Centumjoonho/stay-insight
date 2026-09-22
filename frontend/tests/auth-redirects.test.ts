import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test, { type TestContext } from "node:test";
import { runInNewContext } from "node:vm";
import ts from "typescript";
import { publicAuthUrl, signupRedirectOptions } from "../src/lib/supabase/redirects.ts";

test("signup uses the configured local and production public origins", (t) => {
  for (const origin of ["http://localhost:3000", "https://stay.example.test"]) {
    setSite(t, origin);
    assert.deepEqual(signupRedirectOptions(), { emailRedirectTo: origin + "/auth/callback" });
  }
});

test("public redirects reject missing, malformed and bind-address configuration", (t) => {
  for (const origin of [undefined, "", "invalid", "http://0.0.0.0:3000", "http://0:3000",
    "http://[::]:3000", "ftp://example.test", "https://user:pass@example.test",
    "https://example.test/path", "https://example.test/?next=evil", "https://example.test/#hash"]) {
    setSite(t, origin);
    assert.throws(() => publicAuthUrl("/login"), /NEXT_PUBLIC_SITE_URL/);
  }
});

test("callback success, failure and missing code ignore internal request origin", async (t) => {
  // Execute the actual route with only its framework/Auth boundaries replaced.
  const source = readFileSync(new URL("../src/app/auth/callback/route.ts", import.meta.url), "utf8");
  const javascript = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  for (const origin of ["http://localhost:3000", "https://stay.example.test"]) {
    setSite(t, origin);
    for (const scenario of [
      { code: "fixture", error: null, configured: true, path: "/onboarding" },
      { code: "fixture", error: new Error("invalid code"), configured: true, path: "/login" },
      { code: "", error: null, configured: true, path: "/login" },
      { code: "fixture", error: null, configured: false, path: "/login" },
    ]) {
      let exchanges = 0;
      const exports: { GET?: (request: unknown) => Promise<Response> } = {};
      const dependencies: Record<string, unknown> = {
        "next/server": { NextResponse: { redirect: (url: string) => new Response(null, { status: 307, headers: { location: url } }) } },
        "@/lib/supabase/redirects": { publicAuthUrl },
        "@/lib/supabase/server": { serverAuth: async () => scenario.configured ? {
          auth: { exchangeCodeForSession: async (code: string) => {
            assert.equal(code, scenario.code);
            exchanges++;
            return { error: scenario.error };
          } },
        } : null },
      };
      runInNewContext(javascript, { exports, require: (name: string) => {
        assert.ok(name in dependencies, name);
        return dependencies[name];
      } });
      const url = new URL("http://0.0.0.0:3000/auth/callback");
      if (scenario.code) url.searchParams.set("code", scenario.code);
      const response = await exports.GET!({ url: url.href, nextUrl: url });
      assert.equal(response.headers.get("location"), origin + scenario.path);
      assert.equal(response.headers.get("cache-control"), "private, no-store");
      assert.equal(response.headers.get("location")?.includes("0.0.0.0"), false);
      assert.equal(exchanges, scenario.code && scenario.configured ? 1 : 0);
    }
  }
});

test("protected-route redirect never uses the Docker request origin", async (t) => {
  setSite(t, "http://localhost:3000");
  const source = readFileSync(new URL("../src/proxy.ts", import.meta.url), "utf8");
  const javascript = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const exports: { proxy?: (request: unknown) => Promise<Response> } = {};
  const responseWithCookies = (url?: string) => Object.assign(
    new Response(null, url ? { status: 307, headers: { location: url } } : undefined),
    { cookies: { getAll: () => [], set: () => {} } },
  );
  const dependencies: Record<string, unknown> = {
    "@supabase/ssr": {},
    "@/lib/supabase/config": { authConfiguration: () => null },
    "@/lib/supabase/redirects": { publicAuthUrl },
    "next/server": { NextResponse: {
      next: () => responseWithCookies(),
      redirect: responseWithCookies,
    } },
  };
  runInNewContext(javascript, { exports, require: (name: string) => {
    assert.ok(name in dependencies, name);
    return dependencies[name];
  } });
  for (const path of ["/onboarding", "/properties", "/properties/new"]) {
    const url = new URL(path, "http://0.0.0.0:3000");
    const response = await exports.proxy!({ url: url.href, nextUrl: url });
    assert.equal(response.headers.get("location"), "http://localhost:3000/login");
    assert.equal(response.headers.get("location")?.includes("0.0.0.0"), false);
  }
});

function setSite(t: TestContext, value: string | undefined) {
  const previous = process.env.NEXT_PUBLIC_SITE_URL;
  const assign = (next: string | undefined) => {
    if (next === undefined) delete process.env.NEXT_PUBLIC_SITE_URL;
    else process.env.NEXT_PUBLIC_SITE_URL = next;
  };
  assign(value);
  t.after(() => assign(previous));
}

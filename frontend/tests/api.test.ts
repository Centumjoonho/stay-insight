import assert from "node:assert/strict";
import test from "node:test";
import { apiRequest, ApiError } from "../src/lib/api/transport.ts";

test("API attaches bearer and selected organization and disables caching", async () => {
  const fake: typeof fetch = async (url, options) => {
    assert.equal(url, "https://api.example.test/api/v1/properties");
    const headers = new Headers(options?.headers);
    assert.equal(headers.get("Authorization"), "Bearer signed-token");
    assert.equal(headers.get("X-Organization-Id"), "org");
    assert.equal(options?.cache, "no-store");
    return Response.json({ items: [], total: 0 });
  };
  assert.deepEqual(await apiRequest("https://api.example.test", "signed-token",
    "/api/v1/properties", {}, "org", fake), { items: [], total: 0 });
});
test("missing token does not send a request", async () => {
  let called = false;
  await assert.rejects(apiRequest("https://api.example.test", undefined, "/api/v1/me", {}, undefined,
    async () => { called = true; return Response.json({}); }), (e: unknown) => e instanceof ApiError && e.status === 401);
  assert.equal(called, false);
});
test("401 and 403 keep distinct error semantics and never expose raw server errors", async () => {
  for (const status of [401, 403, 500]) {
    await assert.rejects(apiRequest("https://api.example.test", "token", "/api/v1/me", {}, undefined,
      async () => new Response("private database error", { status })),
      (e: unknown) => e instanceof ApiError && e.status === status && !e.message.includes("database"));
  }
});

import assert from "node:assert/strict";
import test from "node:test";
import { checkBackendHealth } from "../src/lib/health.ts";

test("calls the configured versioned endpoint without caching", async () => {
  const signal = new AbortController().signal;
  const fetcher: typeof fetch = async (input, options) => {
    assert.equal(String(input), "https://api.example.test/api/v1/health");
    assert.equal(options?.cache, "no-store");
    assert.equal(options?.signal, signal);
    return Response.json({ status: "ok" });
  };
  assert.equal(await checkBackendHealth("https://api.example.test/", signal, fetcher), true);
});

test("rejects unavailable, invalid, or unexpected backend responses", async () => {
  for (const response of [new Response(null, { status: 503 }), new Response("invalid"), Response.json({ status: "error" }), Response.json(null)]) {
    assert.equal(await checkBackendHealth("https://api.example.test", new AbortController().signal, async () => response), false);
  }
});

test("missing or invalid configuration never makes a request", async () => {
  let requests = 0;
  const unexpectedFetch: typeof fetch = async () => {
    requests += 1;
    throw new Error("must not call fetch");
  };
  for (const url of [undefined, "", "not a URL", "file:///tmp"]) {
    assert.equal(await checkBackendHealth(url, new AbortController().signal, unexpectedFetch), false);
  }
  assert.equal(requests, 0);
});

test("network failure and cancellation produce unavailable", async () => {
  const controller = new AbortController();
  controller.abort();
  const fetcher: typeof fetch = async (_input, options) => {
    options?.signal?.throwIfAborted();
    throw new TypeError("network unavailable");
  };
  assert.equal(await checkBackendHealth("https://api.example.test", controller.signal, fetcher), false);
  assert.equal(await checkBackendHealth("https://api.example.test", new AbortController().signal, fetcher), false);
});

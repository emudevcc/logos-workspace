import { test } from "node:test";
import assert from "node:assert/strict";

import { ApiError, apiGet, apiPost } from "../../static/js/lib/api.js";

function stubFetch(response) {
  const original = globalThis.fetch;
  globalThis.fetch = async () => response;
  return () => {
    globalThis.fetch = original;
  };
}

test("apiGet returns JSON on 200", async () => {
  const restore = stubFetch(
    new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
  try {
    assert.deepEqual(await apiGet("/x"), { ok: true });
  } finally {
    restore();
  }
});

test("apiGet throws ApiError with detail on non-200", async () => {
  const restore = stubFetch(
    new Response(JSON.stringify({ detail: "boom" }), {
      status: 502,
      headers: { "Content-Type": "application/json" },
    }),
  );
  try {
    await assert.rejects(
      () => apiGet("/x"),
      (error) => error instanceof ApiError && error.status === 502 && error.detail === "boom",
    );
  } finally {
    restore();
  }
});

test("apiPost sends JSON body with POST method", async () => {
  let captured;
  const original = globalThis.fetch;
  globalThis.fetch = async (url, init) => {
    captured = { url, init };
    return new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } });
  };
  try {
    await apiPost("/x", { a: 1 });
    assert.equal(captured.init.method, "POST");
    assert.equal(captured.init.body, JSON.stringify({ a: 1 }));
    assert.equal(captured.init.headers["Content-Type"], "application/json");
  } finally {
    globalThis.fetch = original;
  }
});

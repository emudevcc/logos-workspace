import { test } from "node:test";
import assert from "node:assert/strict";

import { backoffDelay } from "../../static/js/lib/backoff.js";

test("backoff starts at base and doubles", () => {
  assert.equal(backoffDelay(1), 1000);
  assert.equal(backoffDelay(2), 2000);
  assert.equal(backoffDelay(3), 4000);
  assert.equal(backoffDelay(4), 8000);
});

test("backoff caps at maxMs", () => {
  assert.equal(backoffDelay(5), 15000);
  assert.equal(backoffDelay(20), 15000);
});

test("backoff clamps invalid attempts to base", () => {
  assert.equal(backoffDelay(0), 1000);
  assert.equal(backoffDelay(-1), 1000);
});

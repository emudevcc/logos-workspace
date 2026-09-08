import { test } from "node:test";
import assert from "node:assert/strict";

import { formatClock, isExpired, remainingSeconds } from "../../static/js/lib/timer.js";

test("remainingSeconds counts down and floors at zero", () => {
  assert.equal(remainingSeconds(90, 1000, 1000), 90);
  assert.equal(remainingSeconds(90, 1000, 11000), 80);
  assert.equal(remainingSeconds(90, 1000, 100000), 0);
});

test("isExpired flips exactly at duration", () => {
  assert.equal(isExpired(90, 1000, 91000), true);
  assert.equal(isExpired(90, 1000, 89999), false);
});

test("formatClock pads to MM:SS", () => {
  assert.equal(formatClock(90), "01:30");
  assert.equal(formatClock(5), "00:05");
  assert.equal(formatClock(0), "00:00");
});

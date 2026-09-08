import { test } from "node:test";
import assert from "node:assert/strict";

import { createBus } from "../../static/js/lib/bus.js";

test("emit dispatches to matching listeners", () => {
  const bus = createBus();
  const seen = [];
  bus.on("news", (message) => seen.push(message));
  bus.emit("news", { x: 1 });
  bus.emit("other", { x: 2 });
  assert.deepEqual(seen, [{ x: 1 }]);
});

test("unsubscribe removes the listener", () => {
  const bus = createBus();
  const seen = [];
  const off = bus.on("news", (message) => seen.push(message));
  off();
  bus.emit("news", { x: 1 });
  assert.equal(seen.length, 0);
});

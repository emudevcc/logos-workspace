import { test } from "node:test";
import assert from "node:assert/strict";

import { findConnectors } from "../../static/js/lib/connectors.js";

test("finds connectors case-insensitively", () => {
  const matches = findConnectors("Furthermore, we act. On the other hand, cost.");
  const names = matches.map((m) => m.connector);
  assert.ok(names.includes("furthermore"));
  assert.ok(names.includes("on the other hand"));
});

test("returns original index and length", () => {
  const text = "Hello. However, bye.";
  const [match] = findConnectors(text);
  assert.equal(match.connector, "however");
  assert.equal(text.slice(match.index, match.index + match.length), "However");
});

test("does not match inside longer words", () => {
  assert.equal(findConnectors("howevering").length, 0);
});

test("empty text returns no matches", () => {
  assert.deepEqual(findConnectors(""), []);
});

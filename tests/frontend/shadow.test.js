import { test } from "node:test";
import assert from "node:assert/strict";

import { shadowDiff } from "../../static/js/lib/shadow.js";

test("shadowDiff matches words case-insensitively", () => {
  const diff = shadowDiff("We need to align", "we need to align");
  assert.equal(diff.total, 4);
  assert.equal(diff.matched, 4);
  assert.equal(diff.accuracy, 100);
});

test("shadowDiff reports missed words", () => {
  const diff = shadowDiff("We need to align", "we need");
  assert.equal(diff.matched, 2);
  assert.equal(diff.accuracy, 50);
  assert.equal(diff.words[2].matched, false);
});

test("shadowDiff ignores punctuation", () => {
  const diff = shadowDiff("Hello, world!", "hello world");
  assert.equal(diff.matched, 2);
});

test("shadowDiff handles empty input", () => {
  const diff = shadowDiff("", "");
  assert.equal(diff.total, 0);
  assert.equal(diff.accuracy, 0);
});

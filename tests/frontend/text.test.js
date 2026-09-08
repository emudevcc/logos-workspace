import { test } from "node:test";
import assert from "node:assert/strict";

import { countWords, reductionPercent, sanitizePhrase } from "../../static/js/lib/text.js";

test("countWords counts whitespace-separated words", () => {
  assert.equal(countWords("one two three"), 3);
  assert.equal(countWords("  spaced   out  "), 2);
});

test("countWords returns zero for empty input", () => {
  assert.equal(countWords(""), 0);
  assert.equal(countWords(null), 0);
});

test("reductionPercent computes and floors at zero", () => {
  assert.equal(reductionPercent(100, 60), 40);
  assert.equal(reductionPercent(10, 7), 30);
  assert.equal(reductionPercent(0, 0), 0);
  assert.equal(reductionPercent(10, 12), 0);
});

test("sanitizePhrase trims and collapses whitespace", () => {
  assert.equal(sanitizePhrase("  look   forward \n to  "), "look forward to");
  assert.equal(sanitizePhrase("   "), null);
  assert.equal(sanitizePhrase(null), null);
});

test("sanitizePhrase caps length", () => {
  const long = "a".repeat(300);
  assert.equal(sanitizePhrase(long, 200).length, 200);
});

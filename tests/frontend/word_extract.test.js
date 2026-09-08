import { test } from "node:test";
import assert from "node:assert/strict";

import { isWordChar, wordAtOffset } from "../../static/js/lib/word_extract.js";

test("wordAtOffset extracts the surrounding word", () => {
  assert.equal(wordAtOffset("hello world", 2), "hello");
  assert.equal(wordAtOffset("hello world", 8), "world");
});

test("wordAtOffset keeps contractions and compounds intact", () => {
  assert.equal(wordAtOffset("don't stop", 3), "don't");
  assert.equal(wordAtOffset("well-known term", 6), "well-known");
});

test("wordAtOffset on a space prefers the adjacent word", () => {
  assert.equal(wordAtOffset("hello world", 5), "hello");
});

test("wordAtOffset returns null for empty or out-of-range input", () => {
  assert.equal(wordAtOffset("", 0), null);
  assert.equal(wordAtOffset("hello", 99), null);
});

test("isWordChar recognizes word characters only", () => {
  assert.equal(isWordChar("a"), true);
  assert.equal(isWordChar("'"), true);
  assert.equal(isWordChar(" "), false);
  assert.equal(isWordChar("."), false);
});

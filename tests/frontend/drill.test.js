import { test } from "node:test";
import assert from "node:assert/strict";

import { checkIrregularVerb, normalizeAnswer, pickNoRepeat, sameAnswer, shuffle } from "../../static/js/lib/drill.js";

test("normalizeAnswer trims, lowercases, collapses spaces", () => {
  assert.equal(normalizeAnswer("  Went   To  "), "went to");
  assert.equal(normalizeAnswer(null), "");
  assert.equal(normalizeAnswer(undefined), "");
});

test("checkIrregularVerb accepts exact and normalized answers", () => {
  const verb = { past: "went", participle: "gone" };
  assert.deepEqual(checkIrregularVerb(verb, "went", "gone"), {
    pastCorrect: true,
    participleCorrect: true,
  });
  assert.deepEqual(checkIrregularVerb(verb, " Went ", "GONE"), {
    pastCorrect: true,
    participleCorrect: true,
  });
});

test("checkIrregularVerb flags wrong answers", () => {
  const verb = { past: "went", participle: "gone" };
  assert.deepEqual(checkIrregularVerb(verb, "goed", "gone"), {
    pastCorrect: false,
    participleCorrect: true,
  });
  assert.deepEqual(checkIrregularVerb(verb, "goed", "went"), {
    pastCorrect: false,
    participleCorrect: false,
  });
});

test("sameAnswer compares case-insensitively and collapses spaces", () => {
  assert.equal(sameAnswer("rule out", "Rule Out"), true);
  assert.equal(sameAnswer("  decision ", "decision"), true);
  assert.equal(sameAnswer("decide", "decision"), false);
  assert.equal(sameAnswer("", ""), true);
});

test("shuffle returns a permutation of the input", () => {
  const input = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
  const out = shuffle(input);
  assert.equal(out.length, input.length);
  assert.deepEqual([...out].sort(), [...input].sort());
  assert.deepEqual(input, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]); // original untouched
});

test("shuffle handles empty and single-element arrays", () => {
  assert.deepEqual(shuffle([]), []);
  assert.deepEqual(shuffle([7]), [7]);
});

test("pickNoRepeat walks a pool without repeating until exhausted", () => {
  const items = [{ id: "a" }, { id: "b" }, { id: "c" }, { id: "d" }];
  const seen = new Set();
  const picked = [];
  for (let i = 0; i < items.length; i += 1) {
    picked.push(pickNoRepeat(items, seen, (item) => item.id).id);
  }
  // First pass: every item appears exactly once (no fixed order repeats).
  assert.deepEqual(new Set(picked).size, items.length);
  assert.deepEqual(seen.size, items.length);
});

test("pickNoRepeat restarts the cycle once every item is seen", () => {
  const items = [{ id: "x" }, { id: "y" }];
  const seen = new Set();
  const first = pickNoRepeat(items, seen, (item) => item.id);
  const second = pickNoRepeat(items, seen, (item) => item.id);
  const third = pickNoRepeat(items, seen, (item) => item.id);
  assert.notEqual(first.id, second.id); // no immediate repeat
  assert.equal(seen.has(third.id), true); // cycle restarted after exhaustion
});

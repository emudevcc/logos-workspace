import { test } from "node:test";
import assert from "node:assert/strict";

import {
  DEFAULT_FILLERS,
  cadenceLabel,
  countFillers,
  fillerRate,
  paceLabel,
  wordsPerMinute,
} from "../../static/js/lib/speech.js";

test("countFillers counts whole-word fillers", () => {
  assert.equal(countFillers("Um, I like, you know, think so"), 3);
  assert.equal(countFillers("clean sentence"), 0);
});

test("countFillers respects word boundaries", () => {
  assert.equal(countFillers("likely umbrella"), 0);
});

test("wordsPerMinute computes rate", () => {
  assert.equal(wordsPerMinute(120, 60), 120);
  assert.equal(wordsPerMinute(60, 30), 120);
  assert.equal(wordsPerMinute(10, 0), 0);
});

test("default fillers include common ones", () => {
  assert.ok(DEFAULT_FILLERS.includes("um"));
  assert.ok(DEFAULT_FILLERS.includes("you know"));
  assert.ok(DEFAULT_FILLERS.includes("like"));
});

test("fillerRate computes fillers per minute", () => {
  assert.equal(fillerRate(6, 60), 6);
  assert.equal(fillerRate(3, 30), 6);
  assert.equal(fillerRate(0, 0), 0);
});

test("paceLabel classifies wpm", () => {
  assert.equal(paceLabel(80), "slow");
  assert.equal(paceLabel(140), "on-target");
  assert.equal(paceLabel(200), "fast");
});

test("cadenceLabel classifies words per utterance", () => {
  assert.equal(cadenceLabel(0), "—");
  assert.equal(cadenceLabel(3), "choppy");
  assert.equal(cadenceLabel(12), "flowing");
  assert.equal(cadenceLabel(30), "run-on");
});

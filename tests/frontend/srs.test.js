import { test } from "node:test";
import assert from "node:assert/strict";

import { GRADE_LABELS, formatInterval, gradeLabel } from "../../static/js/lib/srs.js";

test("gradeLabel maps 1-4 to labels", () => {
  assert.equal(gradeLabel(1), "Again");
  assert.equal(gradeLabel(2), "Hard");
  assert.equal(gradeLabel(3), "Good");
  assert.equal(gradeLabel(4), "Easy");
  assert.equal(gradeLabel(9), "Unknown");
});

test("formatInterval renders whole days", () => {
  assert.equal(formatInterval(1), "1d");
  assert.equal(formatInterval(15), "15d");
  assert.equal(formatInterval(0), "<1d");
});

test("labels cover grades 1 through 4", () => {
  assert.deepEqual(Object.keys(GRADE_LABELS).sort(), ["1", "2", "3", "4"]);
});

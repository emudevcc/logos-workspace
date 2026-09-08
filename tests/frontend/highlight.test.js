import { test } from "node:test";
import assert from "node:assert/strict";

import { highlightSegments } from "../../static/js/lib/highlight.js";

test("marks discourse connectors", () => {
  const segments = highlightSegments("Go. However, stop.");
  const marked = segments.filter((s) => s.mark).map((s) => s.text);
  assert.deepEqual(marked, ["However"]);
});

test("no connectors yields a single unmarked segment", () => {
  assert.deepEqual(highlightSegments("plain text"), [{ text: "plain text", mark: false }]);
});

test("segments reconstruct the original text", () => {
  const text = "Furthermore, then on the other hand.";
  const segments = highlightSegments(text);
  assert.equal(segments.map((s) => s.text).join(""), text);
});

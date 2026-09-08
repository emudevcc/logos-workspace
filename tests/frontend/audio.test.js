import { test } from "node:test";
import assert from "node:assert/strict";

import { floatTo16BitPCM } from "../../static/js/lib/audio.js";

test("floatTo16BitPCM scales and clamps to 16-bit", () => {
  const samples = new Float32Array([1, -1, 0, -0.5, 2]);
  const pcm = floatTo16BitPCM(samples);
  assert.equal(pcm.length, 5);
  assert.equal(pcm[0], 32767);
  assert.equal(pcm[1], -32768);
  assert.equal(pcm[2], 0);
  assert.equal(pcm[3], -16384);
  assert.equal(pcm[4], 32767); // clamped to 1.0
});

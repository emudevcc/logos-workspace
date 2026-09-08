// Pure PCM helpers for the live radio transcript capture.

/**
 * Convert Float32 samples in [-1, 1] to 16-bit little-endian PCM.
 * @param {Float32Array} samples
 * @returns {Int16Array}
 */
export function floatTo16BitPCM(samples) {
  const out = new Int16Array(samples.length);
  for (let i = 0; i < samples.length; i += 1) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return out;
}

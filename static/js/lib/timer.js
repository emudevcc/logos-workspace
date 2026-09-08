// Pure countdown helpers for the 90-second PREP drill.

/**
 * Whole seconds remaining, never negative.
 * @param {number} durationSec
 * @param {number} startedAtMs epoch milliseconds when the timer started.
 * @param {number} nowMs epoch milliseconds now.
 * @returns {number}
 */
export function remainingSeconds(durationSec, startedAtMs, nowMs) {
  const elapsed = nowMs - startedAtMs;
  return Math.max(0, Math.ceil((durationSec * 1000 - elapsed) / 1000));
}

/**
 * Whether the countdown has reached zero.
 * @param {number} durationSec
 * @param {number} startedAtMs
 * @param {number} nowMs
 * @returns {boolean}
 */
export function isExpired(durationSec, startedAtMs, nowMs) {
  return nowMs - startedAtMs >= durationSec * 1000;
}

/**
 * Format seconds as MM:SS.
 * @param {number} totalSeconds
 * @returns {string}
 */
export function formatClock(totalSeconds) {
  const s = Math.max(0, Math.floor(totalSeconds));
  const mm = Math.floor(s / 60);
  const ss = s % 60;
  return `${String(mm).padStart(2, "0")}:${String(ss).padStart(2, "0")}`;
}

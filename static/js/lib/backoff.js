// Reconnect backoff schedule: 1s, 2s, 4s, 8s, 15s (capped).

/**
 * Delay in milliseconds before a reconnect attempt, following exponential
 * backoff capped at `maxMs`.
 *
 * @param {number} attempt 1-based attempt number.
 * @param {{baseMs?: number, maxMs?: number, factor?: number}} [options]
 * @returns {number}
 */
export function backoffDelay(attempt, options = {}) {
  const { baseMs = 1000, maxMs = 15000, factor = 2 } = options;
  if (!Number.isFinite(attempt) || attempt < 1) {
    return baseMs;
  }
  const raw = baseMs * Math.pow(factor, attempt - 1);
  return Math.min(maxMs, Math.max(baseMs, raw));
}

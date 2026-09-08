// Pure speech-metrics logic for the live coach HUD.

export const DEFAULT_FILLERS = ["you know", "um", "uh", "like", "er", "ah"];

/**
 * Count vocal fillers using whole-word/phrase matching (case-insensitive).
 * @param {string} text
 * @param {string[]} [fillers]
 * @returns {number}
 */
export function countFillers(text, fillers = DEFAULT_FILLERS) {
  const source = String(text ?? "").toLowerCase();
  let count = 0;
  for (const filler of fillers) {
    const pattern = new RegExp(
      `(?<![a-z0-9])${escapeRegExp(filler)}(?![a-z0-9])`,
      "g",
    );
    const matches = source.match(pattern);
    if (matches) count += matches.length;
  }
  return count;
}

/**
 * Words per minute.
 * @param {number} wordCount
 * @param {number} elapsedSec
 * @returns {number}
 */
export function wordsPerMinute(wordCount, elapsedSec) {
  if (elapsedSec <= 0) return 0;
  return Math.round(wordCount / (elapsedSec / 60));
}

/**
 * Fillers per minute.
 * @param {number} fillers
 * @param {number} elapsedSec
 * @returns {number}
 */
export function fillerRate(fillers, elapsedSec) {
  if (elapsedSec <= 0) return 0;
  return Math.round(fillers / (elapsedSec / 60));
}

/**
 * Qualitative pace label from words per minute.
 * @param {number} wpm
 * @returns {"slow" | "on-target" | "fast"}
 */
export function paceLabel(wpm) {
  if (wpm < 110) return "slow";
  if (wpm <= 160) return "on-target";
  return "fast";
}

/**
 * Qualitative cadence label from average words per utterance.
 * @param {number} wordsPerUtterance
 * @returns {string}
 */
export function cadenceLabel(wordsPerUtterance) {
  if (wordsPerUtterance <= 0) return "—";
  if (wordsPerUtterance < 5) return "choppy";
  if (wordsPerUtterance <= 18) return "flowing";
  return "run-on";
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

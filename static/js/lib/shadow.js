// Word-level diff between a target sentence and the learner's spoken repeat.

/**
 * @param {string} target
 * @param {string} spoken
 * @returns {{total: number, matched: number, accuracy: number, words: Array<{word: string, matched: boolean}>}}
 */
export function shadowDiff(target, spoken) {
  const targetWords = tokenize(target);
  const spokenSet = new Set(tokenize(spoken));
  const matched = targetWords.filter((word) => spokenSet.has(word));
  return {
    total: targetWords.length,
    matched: matched.length,
    accuracy: targetWords.length ? Math.round((matched.length / targetWords.length) * 100) : 0,
    words: targetWords.map((word) => ({ word, matched: spokenSet.has(word) })),
  };
}

function tokenize(text) {
  return String(text ?? "")
    .toLowerCase()
    .replace(/[^\w\s']/g, "")
    .split(/\s+/)
    .filter(Boolean);
}

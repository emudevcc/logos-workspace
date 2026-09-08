// Discourse-connector detection (client-side mirror of the backend logic).

export const DISCOURSE_CONNECTORS = [
  "furthermore",
  "moreover",
  "however",
  "nevertheless",
  "nonetheless",
  "on the other hand",
  "on the contrary",
  "therefore",
  "consequently",
  "as a result",
  "in addition",
  "additionally",
  "for example",
  "for instance",
  "in contrast",
  "by contrast",
  "meanwhile",
  "in conclusion",
  "in summary",
  "in particular",
  "similarly",
  "likewise",
];

// Longest-first so multi-word phrases match whole.
const pattern = new RegExp(
  `(?<![A-Za-z0-9])(${[...DISCOURSE_CONNECTORS]
    .sort((a, b) => b.length - a.length)
    .map(escapeRegExp)
    .join("|")})(?![A-Za-z0-9])`,
  "gi",
);

/**
 * Case-insensitive connector matches ordered by character offset.
 * @param {string} text
 * @returns {Array<{connector: string, index: number, length: number}>}
 */
export function findConnectors(text) {
  const source = String(text ?? "");
  const matches = [];
  for (const match of source.matchAll(pattern)) {
    matches.push({
      connector: match[1].toLowerCase(),
      index: match.index,
      length: match[0].length,
    });
  }
  return matches;
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

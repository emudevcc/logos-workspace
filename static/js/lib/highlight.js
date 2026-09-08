// Split text into segments, marking discourse connectors for highlighting.

import { findConnectors } from "./connectors.js";

/**
 * @param {string} text
 * @returns {Array<{text: string, mark: boolean}>}
 */
export function highlightSegments(text) {
  const source = String(text ?? "");
  const matches = findConnectors(source);
  const segments = [];
  let cursor = 0;

  for (const match of matches) {
    if (match.index > cursor) {
      segments.push({ text: source.slice(cursor, match.index), mark: false });
    }
    segments.push({
      text: source.slice(match.index, match.index + match.length),
      mark: true,
    });
    cursor = match.index + match.length;
  }
  if (cursor < source.length) {
    segments.push({ text: source.slice(cursor), mark: false });
  }
  if (!segments.length) {
    segments.push({ text: source, mark: false });
  }
  return segments;
}

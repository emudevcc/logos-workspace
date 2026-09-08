// Extract the word surrounding a character offset in a text string.

const ASCII_WORD = /^[A-Za-z0-9'’\-]$/;
const LATIN_EXTENDED = /^[\u00C0-\u024F]$/;

/**
 * Whether a single character is part of a word (letters, digits, apostrophes,
 * hyphens, and Latin-extended letters for accented words).
 * @param {string} ch
 * @returns {boolean}
 */
export function isWordChar(ch) {
  if (typeof ch !== "string" || ch.length === 0) return false;
  return ASCII_WORD.test(ch) || LATIN_EXTENDED.test(ch);
}

/**
 * Return the word that contains the given character offset, or null.
 * @param {string} text
 * @param {number} offset
 * @returns {string|null}
 */
export function wordAtOffset(text, offset) {
  const source = String(text ?? "");
  if (offset < 0 || offset > source.length) return null;

  const candidates = [offset];
  if (offset === source.length || !isWordChar(source[offset])) {
    candidates.push(offset - 1);
  }

  for (const position of candidates) {
    if (position < 0 || position >= source.length || !isWordChar(source[position])) continue;
    let start = position;
    let end = position;
    while (start > 0 && isWordChar(source[start - 1])) start -= 1;
    while (end < source.length && isWordChar(source[end])) end += 1;
    const word = source.slice(start, end);
    if (word) return word;
  }
  return null;
}

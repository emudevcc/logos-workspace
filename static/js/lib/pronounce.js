// Browser text-to-speech helpers.

import { h } from "./dom.js";

/**
 * Speak text aloud with the browser's speech synthesis.
 * @param {string} text
 * @param {string} [lang] BCP-47 tag, e.g. "en-US" (default) or "pt-BR".
 * @returns {boolean} true if speech synthesis is available
 */
export function pronounce(text, lang = "en-US") {
  if (typeof text !== "string" || !text || !("speechSynthesis" in window)) return false;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = lang;
  window.speechSynthesis.speak(utterance);
  return true;
}

/**
 * Build a small button that pronounces the given text.
 * @param {string} text
 * @param {string} [label]
 * @param {string} [lang] BCP-47 tag, e.g. "en-US" (default) or "pt-BR".
 * @returns {HTMLElement}
 */
export function pronounceButton(text, label = "Pronounce", lang = "en-US") {
  return h("button", {
    type: "button",
    class: "chip",
    "aria-label": label,
    title: label,
    text: label,
    onclick: () => pronounce(text, lang),
  });
}

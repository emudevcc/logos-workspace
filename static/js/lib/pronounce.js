// Browser text-to-speech helpers.

import { h } from "./dom.js";

/**
 * Speak text aloud with the browser's speech synthesis.
 * @param {string} text
 * @returns {boolean} true if speech synthesis is available
 */
export function pronounce(text) {
  if (typeof text !== "string" || !text || !("speechSynthesis" in window)) return false;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "en-US";
  window.speechSynthesis.speak(utterance);
  return true;
}

/**
 * Build a small button that pronounces the given text.
 * @param {string} text
 * @param {string} [label]
 * @returns {HTMLElement}
 */
export function pronounceButton(text, label = "Pronounce") {
  return h("button", {
    type: "button",
    class: "chip",
    "aria-label": label,
    title: label,
    text: label,
    onclick: () => pronounce(text),
  });
}

// Click-any-word dictionary popover: synonyms + IPA + Spanish translation.

import { apiGet, apiPost } from "../lib/api.js";
import { clear, h } from "../lib/dom.js";
import { pronounceButton } from "../lib/pronounce.js";
import { sanitizePhrase } from "../lib/text.js";
import { wordAtOffset } from "../lib/word_extract.js";

const IGNORE_WORDS = new Set([
  "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for", "with",
  "is", "are", "was", "were", "be", "been", "it", "this", "that", "as", "at",
  "by", "from", "we", "you", "they", "he", "she", "i", "me", "my", "your",
  "not", "no", "if", "so", "do", "does", "did", "have", "has", "had",
]);

export function init() {
  // Chromium/Safari only; the kiosk runs Chromium.
  if (!document.caretRangeFromPoint) return;

  const popover = h("div", {
    class: "dict-popover",
    role: "dialog",
    "aria-label": "Word lookup",
    hidden: true,
  });
  document.body.append(popover);

  const cache = new Map();
  let clickX = 0;
  let clickY = 0;

  document.addEventListener("mouseup", onSelectOrClick);

  function onSelectOrClick(event) {
    const target = event.target;
    if (!(target instanceof Element)) return;
    if (
      target.closest(
        "button, a, input, textarea, select, [contenteditable], .dict-popover, .card-title, .focus-close",
      )
    ) {
      return;
    }

    // 1. Multi-word selection (phrasal verb / collocation / sentence).
    const selection = window.getSelection();
    if (selection && !selection.isCollapsed) {
      const phrase = sanitizePhrase(selection.toString());
      if (phrase && phrase.length >= 2) {
        showLookup(phrase, event.clientX, event.clientY);
      } else {
        hide();
      }
      return;
    }

    // 2. Single-word click.
    const range = document.caretRangeFromPoint(event.clientX, event.clientY);
    if (!range || range.startContainer.nodeType !== Node.TEXT_NODE) {
      hide();
      return;
    }

    const word = wordAtOffset(range.startContainer.data, range.startOffset);
    if (!word || word.length < 2 || IGNORE_WORDS.has(word.toLowerCase())) {
      hide();
      return;
    }
    showLookup(word, event.clientX, event.clientY);
  }

  async function showLookup(word, x, y) {
    clickX = x;
    clickY = y;
    popover.hidden = false;
    clear(popover);
    popover.append(h("p", { class: "muted", text: "Looking up…" }));
    position();

    const key = word.toLowerCase();
    let data = cache.get(key);
    if (!data) {
      try {
        data = await apiGet(`/api/dictionary/lookup?word=${encodeURIComponent(key)}`);
        cache.set(key, data);
      } catch (error) {
        clear(popover);
        popover.append(h("p", { class: "error", text: error.message }));
        return;
      }
    }
    render(data);
  }

  function render(data) {
    clear(popover);
    const addBtn = h("button", {
      type: "button",
      class: "chip",
      text: "＋ Add to review",
      onclick: () => addToReview(data, addBtn),
    });
    popover.append(
      h(
        "div",
        { class: "dict-word" },
        h("span", { class: "dict-term", text: data.word }),
        pronounceButton(data.word),
        data.ipa ? h("span", { class: "dict-ipa", text: data.ipa }) : null,
        data.part_of_speech ? h("span", { class: "dict-pos", text: data.part_of_speech }) : null,
      ),
    );
    if (data.spanish) popover.append(h("p", { class: "dict-es", text: data.spanish }));
    if (data.synonyms && data.synonyms.length) {
      popover.append(
        h("p", { class: "dict-syn" }, h("strong", { text: "Synonyms: " }), data.synonyms.join(", ")),
      );
    }
    if (data.example) popover.append(h("p", { class: "dict-example", text: data.example }));
    popover.append(h("div", { class: "chips" }, addBtn));
    popover.hidden = false;
    position();
  }

  async function addToReview(data, button) {
    try {
      await apiPost("/api/srs/cards", {
        front: data.word,
        back: data.spanish || data.word,
        ipa: data.ipa,
        examples: data.example ? [data.example] : [],
      });
      button.textContent = "Added ✓";
      button.disabled = true;
    } catch (error) {
      button.textContent = "Add failed";
    }
  }

  function position() {
    const pad = 12;
    const rect = popover.getBoundingClientRect();
    let left = clickX + pad;
    let top = clickY + pad;
    if (left + rect.width > window.innerWidth) left = clickX - rect.width - pad;
    if (top + rect.height > window.innerHeight) top = clickY - rect.height - pad;
    popover.style.left = `${Math.max(pad, left)}px`;
    popover.style.top = `${Math.max(pad, top)}px`;
  }

  function hide() {
    popover.hidden = true;
  }

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") hide();
  });
  document.addEventListener("scroll", hide, { capture: true, passive: true });
}

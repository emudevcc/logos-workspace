// Word & Idiom of the Day — generated on the fly.
//
// Every page load and every content refresh (⟳ / 30-min cycle) asks the backend
// for a NEW item: the LLM generates a fresh idiom / phrasal verb / collocation
// when configured, and the backend falls back to the curated pool otherwise.
// There is no per-date archive navigation here — the card is deliberately
// always fresh, never the same phrase twice.

import { apiGet, apiPost } from "../lib/api.js";
import { clear, h } from "../lib/dom.js";
import { pronounceButton } from "../lib/pronounce.js";

/**
 * @param {HTMLElement} slot
 * @param {{bus?: {on: Function}}} [ctx]
 */
export function init(slot, ctx) {
  async function load() {
    try {
      const data = await apiGet("/api/word-of-day/random");
      render(data);
    } catch (error) {
      renderError(error);
    }
  }

  function render(data) {
    clear(slot);
    const addBtn = h("button", {
      type: "button",
      class: "chip",
      text: "＋ Add to review",
      onclick: () => addToReview(data, addBtn),
    });
    slot.append(
      h(
        "div",
        { class: "wod-expression" },
        h("span", { class: "wod-term", text: data.expression }),
        pronounceButton(data.expression),
        data.register_tag ? h("span", { class: "tag", text: data.register_tag }) : null,
      ),
      data.ipa ? h("p", { class: "wod-ipa", text: data.ipa }) : null,
      h("p", { class: "wod-def", text: data.definition }),
      h(
        "ul",
        { class: "wod-examples" },
        (data.examples || []).map((example) => h("li", { text: example })),
      ),
      h("div", { class: "chips" }, addBtn),
    );
  }

  async function addToReview(data, button) {
    try {
      await apiPost("/api/srs/cards", {
        front: data.expression,
        back: data.definition,
        ipa: data.ipa,
        register_tag: data.register_tag,
        examples: data.examples,
      });
      button.textContent = "Added ✓";
      button.disabled = true;
    } catch (error) {
      button.textContent = "Add failed";
    }
  }

  function renderError(error) {
    clear(slot);
    slot.append(
      h("p", { class: "error", text: `Could not load a word: ${error.message}` }),
      h("button", { type: "button", class: "chip", text: "Try again", onclick: load }),
    );
  }

  load();
  ctx?.bus?.on("content:refresh", load);
}

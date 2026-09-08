// Register-swap exercise: rewrite a sentence in a target register.

import { apiPost } from "../lib/api.js";
import { clear, h } from "../lib/dom.js";

/**
 * @param {HTMLElement} slot
 */
export function init(slot) {
  const textarea = h("textarea", {
    class: "declutter-input",
    rows: "3",
    placeholder: "Paste a sentence…",
    "aria-label": "Sentence to rewrite",
  });
  const select = h(
    "select",
    { class: "station-select", "aria-label": "Target register" },
    h("option", { value: "Executive", text: "Executive" }),
    h("option", { value: "Informal", text: "Informal" }),
    h("option", { value: "Technical", text: "Technical" }),
    h("option", { value: "Polite", text: "Polite" }),
    h("option", { value: "Hedged", text: "Hedged" }),
  );
  const button = h("button", { class: "primary", type: "button", text: "Rewrite", onclick: rewrite });
  const resultEl = h("div", { class: "declutter-result", "aria-live": "polite" });

  slot.append(textarea, select, button, resultEl);

  async function rewrite() {
    const text = textarea.value.trim();
    if (!text) return;
    button.disabled = true;
    try {
      const data = await apiPost("/api/register/rewrite", {
        text,
        register_tag: select.value,
      });
      clear(resultEl);
      resultEl.append(
        h("div", { class: "bluf" }, h("strong", { text: `${select.value}: ` }), data.rewritten),
      );
    } catch (error) {
      clear(resultEl);
      resultEl.append(h("p", { class: "error", text: error.message }));
    } finally {
      button.disabled = false;
    }
  }
}

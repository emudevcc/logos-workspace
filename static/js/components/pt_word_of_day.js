// Palavra do dia (Português) — curated PT-BR word with a Spanish note.
//
// A fresh item is requested on every load and on each content refresh cycle,
// with an "add to review" action that saves the card into the PT cockpit.

import { apiGet, apiPost } from "../lib/api.js";
import { clear, h } from "../lib/dom.js";
import { pronounceButton } from "../lib/pronounce.js";

const CATEGORY_LABELS = {
  palavra: "palavra",
  expressao: "expressão",
  colocacao: "colocação",
};

/**
 * @param {HTMLElement} slot
 * @param {{bus?: {on: Function}}} [ctx]
 */
export function init(slot, ctx) {
  async function load() {
    try {
      const data = await apiGet("/api/pt/word-of-day/random");
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
      text: "＋ Revisar depois",
      onclick: () => addToReview(data, addBtn),
    });
    const pieces = [
      h(
        "div",
        { class: "wod-expression" },
        h("span", { class: "wod-term", text: data.expression }),
        pronounceButton(data.expression, "Ouvir", "pt-BR"),
        h("span", { class: "tag", text: CATEGORY_LABELS[data.category] || data.category }),
      ),
      h("p", { class: "wod-def", text: data.definition_pt }),
    ];
    if (data.nota_es) pieces.push(h("p", { class: "es-note", text: `🇪🇸 ${data.nota_es}` }));
    if (data.examples && data.examples.length) {
      pieces.push(
        h(
          "ul",
          { class: "wod-examples" },
          data.examples.map((example) => h("li", { text: example })),
        ),
      );
    }
    pieces.push(h("div", { class: "chips" }, addBtn));
    slot.append(...pieces);
  }

  async function addToReview(data, button) {
    try {
      await apiPost("/api/srs/cards?cockpit=pt", {
        front: data.expression,
        back: data.definition_pt,
        l1_hint: data.nota_es,
        register_tag: CATEGORY_LABELS[data.category] || data.category,
        examples: data.examples,
      });
      button.textContent = "Adicionado ✓";
      button.disabled = true;
    } catch {
      button.textContent = "Falhou ao adicionar";
    }
  }

  function renderError(error) {
    clear(slot);
    slot.append(
      h("p", { class: "error", text: `Não consegui carregar a palavra: ${error.message}` }),
      h("button", { type: "button", class: "chip", text: "Tentar de novo", onclick: load }),
    );
  }

  load();
  ctx?.bus?.on("content:refresh", load);
}

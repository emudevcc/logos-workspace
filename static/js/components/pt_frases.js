// Frases para repetir (Português) — practice sentences with Spanish notes.

import { apiGet } from "../lib/api.js";
import { clear, h } from "../lib/dom.js";
import { pronounceButton } from "../lib/pronounce.js";

/**
 * @param {HTMLElement} slot
 */
export function init(slot) {
  const sentenceEl = h("p", { class: "pt-sentence" });
  const noteEl = h("div");
  const statusEl = h("p", { class: "srs-status", "aria-live": "polite" });
  const nextBtn = h("button", { type: "button", class: "chip", text: "Outra frase", onclick: load });
  const listenBtn = h("button", { type: "button", class: "chip" });
  let busy = false;

  async function load() {
    if (busy) return;
    busy = true;
    nextBtn.disabled = true;
    try {
      const data = await apiGet("/api/pt/practice/sentence");
      clear(noteEl);
      sentenceEl.textContent = data.frase;
      listenBtn.replaceChildren();
      listenBtn.append(pronounceButton(data.frase, "Ouvir 🔊", "pt-BR"));
      if (data.nota_es) noteEl.append(h("p", { class: "es-note", text: `🇪🇸 ${data.nota_es}` }));
      if (data.dica) noteEl.append(h("p", { class: "pt-dica", text: `💡 ${data.dica}` }));
      statusEl.textContent = "";
    } catch (error) {
      statusEl.textContent = `Não consegui carregar: ${error.message}`;
    } finally {
      busy = false;
      nextBtn.disabled = false;
    }
  }

  slot.append(
    sentenceEl,
    h("div", { class: "chips" }, nextBtn, listenBtn),
    noteEl,
    statusEl,
  );
  load();
}

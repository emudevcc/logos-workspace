// Estudo Bíblico — pericope exegesis report generator (Bíblia cockpit).
//
// Submits a passage reference to /api/bible/study (six-section report, saved
// server-side) and renders the result. Content is in Spanish (study output);
// chrome instructions are in Portuguese.

import { apiPost } from "../lib/api.js";
import { renderStudy } from "../lib/bible_render.js";
import { clear, h } from "../lib/dom.js";

const EXAMPLES = [
  "Romanos 8:31-39",
  "João 3:16",
  "Isaías 53",
  "Salmos 23",
  "1 Coríntios 13:4-7",
  "Mateus 5:1-12",
];

/**
 * @param {HTMLElement} slot
 */
export function init(slot) {
  const input = h("input", {
    class: "study-input",
    type: "text",
    placeholder: "Ex.: Romanos 8:31-39 (ou Rm 8:31-39, Juan 3:16…)",
    autocomplete: "off",
  });
  const runBtn = h("button", { type: "button", class: "chip", text: "Estudar passagem" });
  const statusEl = h("p", { class: "srs-status", "aria-live": "polite" });
  const out = h("div", { class: "bible-out" });
  let busy = false;

  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      run();
    }
  });
  runBtn.addEventListener("click", run);

  async function run() {
    const reference = input.value.trim();
    if (!reference || busy) return;
    busy = true;
    runBtn.disabled = true;
    runBtn.textContent = "Estudando…";
    clear(out);
    statusEl.textContent = "";
    try {
      const record = await apiPost("/api/bible/study", { reference });
      renderStudy(out, record);
      statusEl.textContent = `Estudo salvo no histórico (nº ${record.id}).`;
    } catch (error) {
      statusEl.textContent = `Não consegui estudar a passagem: ${error.message}`;
    } finally {
      busy = false;
      runBtn.disabled = false;
      runBtn.textContent = "Estudar passagem";
    }
  }

  const chips = EXAMPLES.map((example) =>
    h("button", {
      type: "button",
      class: "chip",
      text: example,
      title: example,
      onclick: () => {
        input.value = example;
        run();
      },
    }),
  );

  slot.append(
    h(
      "p",
      { text: "Escolha uma passagem de 5–15 versículos para um estudo exegético profundo." },
    ),
    input,
    h("div", { class: "chips" }, runBtn),
    statusEl,
    out,
    h("div", { class: "chips" }, ...chips),
    h("p", {
      class: "bible-note",
      text: "Texto padrão: Reina-Valera (1909) via API.Bible, domínio público quando aplicável. "
        + "A tradução RVR60 não está no catálogo espanhol da API.Bible; use BIBLE_DEFAULT_TRANSLATION "
        + "ao integrar outra fonte. Os estudos seguem método histórico-gramatical e salvaguardas "
        + "evangélicas (sola Scriptura, sem alegorização especulativa).",
    }),
  );
  input.focus();
}

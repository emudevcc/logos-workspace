// Estudo Bíblico — pericope exegesis report generator (Bíblia cockpit).
//
// Submits a passage reference to /api/bible/study (six-section report, saved
// server-side) and renders the result. The passage TEXT can be read in
// Español / English / Português (defaults from /api/bible/prefs — NTV, NIV,
// NVT), while the study output stays in Spanish, the reader's native base.

import { apiGet, apiPost } from "../lib/api.js";
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

const LANG_KEY = "logos-workspace.bible-lang";
const LANG_LABELS = [
  { key: "es", label: "Español" },
  { key: "en", label: "English" },
  { key: "pt", label: "Português" },
];

const FALLBACK_PREFS = { es: "NTV", en: "NIV", pt: "NVT" };

/**
 * @param {HTMLElement} slot
 */
export function init(slot) {
  const input = h("input", {
    class: "study-input",
    type: "text",
    placeholder: "Ej.: Romanos 8:31-39 (o Rm 8:31-39, Juan 3:16…)",
    autocomplete: "off",
  });
  const runBtn = h("button", { type: "button", class: "chip", text: "Estudiar pasaje" });
  const statusEl = h("p", { class: "srs-status", "aria-live": "polite" });
  const out = h("div", { class: "bible-out" });
  const langBar = h("div", { class: "segmented study-lang", role: "group", "aria-label": "Language of the Bible text" });
  const translationEl = h("p", { class: "bible-note study-version" });

  let busy = false;
  let language = readLang();
  let prefs = { ...FALLBACK_PREFS };

  function readLang() {
    try {
      const raw = localStorage.getItem(LANG_KEY);
      if (["es", "en", "pt"].includes(raw)) return raw;
    } catch {
      /* storage unavailable */
    }
    return "es";
  }

  function persistLang(lang) {
    try {
      localStorage.setItem(LANG_KEY, lang);
    } catch {
      /* storage unavailable */
    }
  }

  function renderLangBar() {
    clear(langBar);
    for (const item of LANG_LABELS) {
      const button = h("button", { type: "button", class: "chip", text: item.label });
      button.addEventListener("click", () => {
        language = item.key;
        persistLang(item.key);
        renderLangBar();
        renderVersion();
      });
      langBar.append(button);
    }
    setLangActive();
  }

  function setLangActive() {
    langBar.querySelectorAll(".chip").forEach((button, index) => {
      const item = LANG_LABELS[index];
      button.classList.toggle("is-active", Boolean(item && item.key === language));
    });
  }

  function versionLabel() {
    return (prefs[language] || FALLBACK_PREFS[language] || "…");
  }

  function renderVersion() {
    translationEl.textContent = `Texto del pasaje: ${versionLabel()} · explicación en español.`;
  }

  async function loadPrefs() {
    try {
      prefs = { ...FALLBACK_PREFS, ...(await apiGet("/api/bible/prefs")) };
    } catch {
      /* keep fallback labels */
    }
    renderVersion();
  }

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
    runBtn.textContent = "Estudiando…";
    clear(out);
    statusEl.textContent = "";
    try {
      const record = await apiPost("/api/bible/study", {
        reference,
        translation: versionLabel(),
      });
      renderStudy(out, record);
      statusEl.textContent = `Estudio guardado en el historial (nº ${record.id}).`;
    } catch (error) {
      statusEl.textContent = `No pude estudiar el pasaje: ${error.message}`;
    } finally {
      busy = false;
      runBtn.disabled = false;
      runBtn.textContent = "Estudiar pasaje";
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

  renderLangBar();
  slot.append(
    h(
      "p",
      { text: "Elige un pasaje de 5–15 versículos para un estudio exegético profundo." },
    ),
    langBar,
    translationEl,
    input,
    h("div", { class: "chips" }, runBtn),
    statusEl,
    out,
    h("div", { class: "chips" }, ...chips),
    h("p", {
      class: "bible-note",
      text: "Textos vía API.Bible (NTV es · NIV en · NVT pt — dominio/licencia de tu cuenta). "
        + "Los estudios siguen el método histórico-gramatical con salvaguardas "
        + "evangélicas (sola Scriptura, sin alegorización especulativa).",
    }),
  );
  loadPrefs();
  input.focus();
}

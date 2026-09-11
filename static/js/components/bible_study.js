// Estudo Bíblico — pericope exegesis report generator (Bíblia cockpit).
//
// A flag selector picks the language of the whole study experience
// (🇪🇸 Español · 🇺🇸 English · 🇧🇷 Português; Spanish default). Switching the
// language updates the instructions AND re-generates the current study in the
// new language (the passage text and the six-section report follow along).

import { apiGet, apiPost } from "../lib/api.js";
import { renderStudy } from "../lib/bible_render.js";
import { clear, h } from "../lib/dom.js";

const LANG_OPTIONS = [
  { key: "es", label: "🇪🇸 Español" },
  { key: "en", label: "🇺🇸 English" },
  { key: "pt", label: "🇧🇷 Português" },
];

const LANG_KEY = "logos-workspace.bible-lang";
const FALLBACK_PREFS = { es: "NTV", en: "NIV", pt: "NVT" };

const I18N = {
  es: {
    intro: "Elige un pasaje de 5–15 versículos para un estudio exegético profundo.",
    examples: [
      "Romanos 8:31-39",
      "Juan 3:16",
      "Isaías 53",
      "Salmos 23",
      "1 Corintios 13:4-7",
      "Mateo 5:1-12",
    ],
    placeholder: "Ej.: Romanos 8:31-39 (o Rm 8:31-39, Juan 3:16…)",
    run: "Estudiar pasaje",
    busy: "Estudiando…",
    saved: (id) => `Estudio guardado en el historial (nº ${id}).`,
    regenerated: "Se generó de nuevo en el idioma seleccionado.",
    failed: (message) => `No pude estudiar el pasaje: ${message}`,
    rateLimited: "El servicio de IA está saturado en este momento (429). Espera unos segundos y vuelve a intentarlo.",
    retry: "Reintentar",
    versionPrefix: "Texto del pasaje",
    versionSuffix: "explicación en español",
    note:
      "Textos vía API.Bible (NTV es · NIV en · NVT pt — dominio/licencia de tu cuenta). "
      + "Los estudios siguen el método histórico-gramatical con salvaguardas "
      + "evangélicas (sola Scriptura, sin alegorización especulativa).",
  },
  en: {
    intro: "Choose a 5–15 verse passage for an in-depth exegetical study.",
    examples: [
      "Romans 8:31-39",
      "John 3:16",
      "Isaiah 53",
      "Psalms 23",
      "1 Corinthians 13:4-7",
      "Matthew 5:1-12",
    ],
    placeholder: "E.g. Romans 8:31-39 (or Rm 8:31-39, Juan 3:16…)",
    run: "Study passage",
    busy: "Studying…",
    saved: (id) => `Study saved to history (#${id}).`,
    regenerated: "Regenerated in the selected language.",
    failed: (message) => `Could not study the passage: ${message}`,
    rateLimited: "The AI service is rate-limited right now (429). Wait a few seconds and try again.",
    retry: "Try again",
    versionPrefix: "Passage text",
    versionSuffix: "explanation in English",
    note:
      "Texts via API.Bible (NTV es · NIV en · NVT pt — license from your account). "
      + "Studies follow the historical-grammatical method with evangelical "
      + "guardrails (sola Scriptura, no speculative allegorization).",
  },
  pt: {
    intro: "Escolha uma passagem de 5–15 versículos para um estudo exegético profundo.",
    examples: [
      "Romanos 8:31-39",
      "João 3:16",
      "Isaías 53",
      "Salmos 23",
      "1 Coríntios 13:4-7",
      "Mateus 5:1-12",
    ],
    placeholder: "Ex.: Romanos 8:31-39 (ou Rm 8:31-39, Juan 3:16…)",
    run: "Estudar passagem",
    busy: "Estudando…",
    saved: (id) => `Estudo salvo no histórico (nº ${id}).`,
    regenerated: "Regenerado no idioma selecionado.",
    failed: (message) => `Não consegui estudar a passagem: ${message}`,
    rateLimited: "O serviço de IA está sobrecarregado neste momento (429). Aguarde alguns segundos e tente novamente.",
    retry: "Tentar novamente",
    versionPrefix: "Texto da passagem",
    versionSuffix: "explicação em português",
    note:
      "Textos via API.Bible (NTV es · NIV en · NVT pt — domínio/licença da sua conta). "
      + "Os estudos seguem o método histórico-gramatical com salvaguardas "
      + "evangélicas (sola Scriptura, sem alegorização especulativa).",
  },
};

/**
 * @param {HTMLElement} slot
 */
export function init(slot) {
  const input = h("input", { class: "study-input", type: "text", autocomplete: "off" });
  const runBtn = h("button", { type: "button", class: "chip" });
  const statusEl = h("p", { class: "srs-status", "aria-live": "polite" });
  const out = h("div", { class: "bible-out" });
  const introEl = h("p");
  const langBar = h("div", {
    class: "segmented study-lang",
    role: "group",
    "aria-label": "Idioma del estudio",
  });
  const versionEl = h("p", { class: "bible-note study-version" });
  const noteEl = h("p", { class: "bible-note" });
  const retryBtn = h("button", { type: "button", class: "chip" });
  retryBtn.hidden = true;
  retryBtn.addEventListener("click", () => run());
  const chipsEl = h("div", { class: "chips" });

  let busy = false;
  let language = readLang();
  let prefs = { ...FALLBACK_PREFS };
  let lastReference = null;
  let lastFailAt = 0;

  function t() {
    return I18N[language] || I18N.es;
  }

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

  function versionLabel() {
    return prefs[language] || FALLBACK_PREFS[language] || "…";
  }

  function applyChrome() {
    const strings = t();
    introEl.textContent = strings.intro;
    input.placeholder = strings.placeholder;
    runBtn.textContent = strings.run;
    versionEl.textContent = `${strings.versionPrefix}: ${versionLabel()} · ${strings.versionSuffix}`;
    noteEl.textContent = strings.note;
    renderChips(strings.examples || []);
  }

  function renderChips(examples) {
    clear(chipsEl);
    for (const example of examples) {
      chipsEl.append(
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
    }
  }

  function renderLangBar() {
    clear(langBar);
    for (const item of LANG_OPTIONS) {
      const button = h("button", { type: "button", class: "chip", text: item.label });
      button.addEventListener("click", () => {
        if (item.key === language) return;
        language = item.key;
        persistLang(item.key);
        renderLangBar();
        applyChrome();
        // If a study is already displayed, regenerate it in the new language —
        // unless the last run just failed with a rate limit (no auto-storms).
        const coolingDown = Date.now() - lastFailAt < 8000;
        if (lastReference && !busy && !coolingDown) {
          input.value = lastReference;
          run(true);
        } else {
          statusEl.textContent = coolingDown ? t().rateLimited : "";
          retryBtn.hidden = !coolingDown;
        }
      });
      langBar.append(button);
    }
    setLangActive();
  }

  function setLangActive() {
    langBar.querySelectorAll(".chip").forEach((button, index) => {
      const item = LANG_OPTIONS[index];
      button.classList.toggle("is-active", Boolean(item && item.key === language));
    });
  }

  async function loadPrefs() {
    try {
      prefs = { ...FALLBACK_PREFS, ...(await apiGet("/api/bible/prefs")) };
    } catch {
      /* keep fallback labels */
    }
    applyChrome();
  }

  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      run();
    }
  });
  runBtn.addEventListener("click", run);

  async function run(regenerated = false) {
    const reference = input.value.trim();
    if (!reference || busy) return;
    busy = true;
    lastReference = reference;
    runBtn.disabled = true;
    retryBtn.hidden = true;
    runBtn.textContent = t().busy;
    clear(out);
    statusEl.textContent = "";
    try {
      const record = await apiPost("/api/bible/study", {
        reference,
        translation: versionLabel(),
        language,
      });
      renderStudy(out, record, language);
      statusEl.textContent = regenerated
        ? `${t().saved(record.id)} ${t().regenerated}`
        : t().saved(record.id);
    } catch (error) {
      const limited = error.status === 429;
      if (limited) lastFailAt = Date.now();
      statusEl.textContent = limited ? t().rateLimited : t().failed(error.message);
      if (!limited) retryBtn.hidden = true;
      else {
        retryBtn.textContent = t().retry;
        retryBtn.hidden = false;
      }
    } finally {
      busy = false;
      runBtn.disabled = false;
      runBtn.textContent = t().run;
    }
  }

  slot.append(introEl, langBar, versionEl, input, h("div", { class: "chips" }, runBtn, retryBtn), statusEl, out);
  slot.append(chipsEl, noteEl);

  renderLangBar();
  applyChrome();
  loadPrefs();
  input.focus();
}

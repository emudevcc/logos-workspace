// Shared renderer for a full Bíblia study report (six sections), localized
// to the study's output language (es/en/pt — Spanish default).

import { h } from "./dom.js";

const LABELS = {
  es: {
    section1: "1 · Marco literario del texto",
    genre: "Género",
    tone: "Tono del autor",
    unit: "División de la unidad",
    section2: "2 · Contexto histórico-gramatical",
    author: "Autor",
    recipients: "Destinatarios",
    date: "Fecha aproximada",
    geo: "Contexto geopolítico",
    occasion: "Ocasión",
    section3: "3 · Exégesis léxica y gramatical",
    noTerms: "Sin términos analizados.",
    lemma: "Lemma",
    parsing: "Análisis morfosintáctico",
    definition: "Definición contextual",
    consensus: "Consenso documentado: ",
    section4: "4 · Contexto redentor y teológico",
    redemption: "Lugar en la historia de la redención",
    cross: "Referencias cruzadas",
    christ: "Significado cristológico",
    section5: "5 · Principio central y atemporal",
    section6: "6 · Aplicación práctica",
    actions: "Acciones concretas",
    reflections: "Preguntas de reflexión",
    obedience: "Áreas de obediencia",
    notes: "Notas: ",
  },
  en: {
    section1: "1 · Literary framework of the text",
    genre: "Genre",
    tone: "Authorial tone",
    unit: "Unit division",
    section2: "2 · Historical-grammatical context",
    author: "Author",
    recipients: "Recipients",
    date: "Approximate date",
    geo: "Geopolitical context",
    occasion: "Occasion",
    section3: "3 · Lexical and grammatical exegesis",
    noTerms: "No terms analyzed.",
    lemma: "Lemma",
    parsing: "Morphosyntactic analysis",
    definition: "Contextual definition",
    consensus: "Documented consensus: ",
    section4: "4 · Redemptive and theological context",
    redemption: "Place in redemptive history",
    cross: "Cross-references",
    christ: "Christological significance",
    section5: "5 · Core timeless principle",
    section6: "6 · Practical application",
    actions: "Concrete actions",
    reflections: "Reflection questions",
    obedience: "Areas of obedience",
    notes: "Notes: ",
  },
  pt: {
    section1: "1 · Marco literário do texto",
    genre: "Gênero",
    tone: "Tom do autor",
    unit: "Divisão da unidade",
    section2: "2 · Contexto histórico-gramatical",
    author: "Autor",
    recipients: "Destinatários",
    date: "Data aproximada",
    geo: "Contexto geopolítico",
    occasion: "Ocasião",
    section3: "3 · Exegese lexical e gramatical",
    noTerms: "Nenhum termo analisado.",
    lemma: "Lema",
    parsing: "Análise morfossintática",
    definition: "Definição contextual",
    consensus: "Consenso documentado: ",
    section4: "4 · Contexto redentivo e teológico",
    redemption: "Lugar na história da redenção",
    cross: "Referências cruzadas",
    christ: "Significado cristológico",
    section5: "5 · Princípio central e atemporal",
    section6: "6 · Aplicação prática",
    actions: "Ações concretas",
    reflections: "Perguntas de reflexão",
    obedience: "Áreas de obediência",
    notes: "Notas: ",
  },
};

/**
 * Language of a saved study from its translation label (via the prefs map).
 * @param {{es?: string, en?: string, pt?: string}} [prefs]
 * @param {string} [label]
 * @returns {string}
 */
export function translationLanguage(prefs, label) {
  if (prefs && label === prefs.en) return "en";
  if (prefs && label === prefs.pt) return "pt";
  return "es";
}

/**
 * Render a complete study record into a container, localized to ``lang``.
 * @param {HTMLElement} slot
 * @param {object} record
 * @param {string} [lang] es | en | pt
 */
export function renderStudy(slot, record, lang = "es") {
  const L = LABELS[lang] || LABELS.es;
  const report = record.report || record;
  const ref = report.reference || record.reference || "";
  const translation = report.translation || record.translation || "";

  slot.append(
    h("h3", { class: "bible-ref", text: `${ref}${translation ? ` · ${translation}` : ""}` }),
    h("div", { class: "bible-text", text: report.passage_text }),
    h("h4", { class: "bible-section-title", text: L.section1 }),
    row(L.genre, report.text_literary?.genre),
    row(L.tone, report.text_literary?.authorial_tone),
    row(L.unit, report.text_literary?.unit_division),
    h("h4", { class: "bible-section-title", text: L.section2 }),
    row(L.author, report.historical_grammatical?.author),
    row(L.recipients, report.historical_grammatical?.recipients),
    row(L.date, report.historical_grammatical?.date),
    row(L.geo, report.historical_grammatical?.geopolitical_context),
    row(L.occasion, report.historical_grammatical?.occasion),
    h("h4", { class: "bible-section-title", text: L.section3 }),
  );

  const lexical = report.lexical_exegesis || [];
  if (!lexical.length) {
    slot.append(h("p", { class: "muted", text: L.noTerms }));
  } else {
    const list = h("ul", { class: "bible-lexical" });
    for (const item of lexical) {
      const li = h(
        "li",
        h(
          "p",
          { class: "bible-term" },
          h("strong", { text: item.term || "" }),
          item.transliteration ? ` (${item.transliteration})` : "",
        ),
      );
      li.append(row(L.lemma, item.lemma));
      li.append(row(L.parsing, item.parsing));
      li.append(row(L.definition, item.contextual_definition));
      if (item.consensus_note) {
        li.append(h("p", { class: "bible-note", text: `${L.consensus}${item.consensus_note}` }));
      }
      list.append(li);
    }
    slot.append(list);
  }

  slot.append(
    h("h4", { class: "bible-section-title", text: L.section4 }),
    row(L.redemption, report.redemptive_theological?.placement_redemptive_history),
  );
  const cross = report.redemptive_theological?.cross_references || [];
  if (cross.length) {
    slot.append(row(L.cross, h("span", { text: cross.join(" · ") })));
  }
  slot.append(
    row(L.christ, report.redemptive_theological?.christological_significance),
    h("h4", { class: "bible-section-title", text: L.section5 }),
    h("p", { class: "bible-principle", text: report.core_principle }),
    h("h4", { class: "bible-section-title", text: L.section6 }),
    listSection(L.actions, report.practical_application?.action_items),
    listSection(L.reflections, report.practical_application?.reflection_prompts),
    listSection(L.obedience, report.practical_application?.obedience_areas),
  );
  if (report.guardrail_notes) {
    slot.append(h("p", { class: "bible-note", text: `${L.notes}${report.guardrail_notes}` }));
  }
}

function row(label, value) {
  if (value === undefined || value === null || value === "") return null;
  return h(
    "p",
    { class: "bible-row" },
    h("span", { class: "bible-label", text: `${label}: ` }),
    value instanceof Node ? value : h("span", { text: String(value) }),
  );
}

function listSection(title, items) {
  if (!items || !items.length) return null;
  const list = h("ul", { class: "bible-app" });
  for (const item of items) {
    list.append(h("li", { text: item }));
  }
  return h("div", {}, h("h5", { class: "bible-subtitle", text: title }), list);
}

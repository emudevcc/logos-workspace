// Shared renderer for a full Bíblia study report (six sections).

import { h } from "./dom.js";

/**
 * Render a complete study record (StudyRecord JSON) into a container.
 * @param {HTMLElement} slot
 * @param {object} record
 */
export function renderStudy(slot, record) {
  const report = record.report || record;
  const ref = report.reference || record.reference || "";
  const translation = report.translation || record.translation || "";

  slot.append(
    h("h3", { class: "bible-ref", text: `${ref}${translation ? ` · ${translation}` : ""}` }),
    h("div", { class: "bible-text", text: report.passage_text }),
    h("h4", { class: "bible-section-title", text: "1 · Marco literario del texto" }),
    row("Género", report.text_literary?.genre),
    row("Tono del autor", report.text_literary?.authorial_tone),
    row("División de la unidad", report.text_literary?.unit_division),
    h("h4", { class: "bible-section-title", text: "2 · Contexto histórico-gramatical" }),
    row("Autor", report.historical_grammatical?.author),
    row("Destinatarios", report.historical_grammatical?.recipients),
    row("Fecha aproximada", report.historical_grammatical?.date),
    row("Contexto geopolítico", report.historical_grammatical?.geopolitical_context),
    row("Ocasión", report.historical_grammatical?.occasion),
    h("h4", { class: "bible-section-title", text: "3 · Exégesis léxica y gramatical" }),
  );

  const lexical = report.lexical_exegesis || [];
  if (!lexical.length) {
    slot.append(h("p", { class: "muted", text: "Sin términos analizados." }));
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
      li.append(row("Lemma", item.lemma));
      li.append(row("Análisis morfosintáctico", item.parsing));
      li.append(row("Definición contextual", item.contextual_definition));
      if (item.consensus_note) {
        li.append(h("p", { class: "bible-note", text: `Consenso documentado: ${item.consensus_note}` }));
      }
      list.append(li);
    }
    slot.append(list);
  }

  slot.append(
    h("h4", { class: "bible-section-title", text: "4 · Contexto redentor y teológico" }),
    row("Lugar en la historia de la redención", report.redemptive_theological?.placement_redemptive_history),
  );
  const cross = report.redemptive_theological?.cross_references || [];
  if (cross.length) {
    slot.append(
      row("Referencias cruzadas", h("span", { text: cross.join(" · ") })),
    );
  }
  slot.append(
    row("Significado cristológico", report.redemptive_theological?.christological_significance),
    h("h4", { class: "bible-section-title", text: "5 · Principio central y atemporal" }),
    h("p", { class: "bible-principle", text: report.core_principle }),
    h("h4", { class: "bible-section-title", text: "6 · Aplicación práctica" }),
    listSection("Acciones concretas", report.practical_application?.action_items),
    listSection("Preguntas de reflexión", report.practical_application?.reflection_prompts),
    listSection("Áreas de obediencia", report.practical_application?.obedience_areas),
  );
  if (report.guardrail_notes) {
    slot.append(h("p", { class: "bible-note", text: `Notas: ${report.guardrail_notes}` }));
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
  return h("div", null, h("h5", { class: "bible-subtitle", text: title }), list);
}

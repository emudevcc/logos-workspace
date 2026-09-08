// Spaced-repetition flashcard deck (keyboard: Space to flip, 1-4 to grade).
//
// Cockpit-aware: decks are loaded for the active cockpit (?cockpit=), so the
// same component serves the English and the Português cockpits. When the PT
// cockpit is active the visible labels switch to Portuguese and the front is
// pronounced with a pt-BR voice.

import { apiGet, apiPost } from "../lib/api.js";
import { getActiveCockpit } from "../lib/cockpit.js";
import { clear, h } from "../lib/dom.js";
import { pronounceButton } from "../lib/pronounce.js";
import { formatInterval, gradeLabel } from "../lib/srs.js";

/**
 * @param {HTMLElement} slot
 */
export function init(slot) {
  let cards = [];
  let index = 0;
  let flipped = false;
  let busy = false;

  const cockpit = getActiveCockpit(window.localStorage);
  const pt = cockpit === "pt";
  const lang = pt ? "pt-BR" : "en-US";
  const ui = pt
    ? {
        export: "Exportar",
        noDecks: "Nenhum baralho ainda.",
        newTag: "Novo",
        reviewTag: "Revisão",
        hintFlip: "Espaço para virar · 1–4 para avaliar",
        done: "Tudo em dia — sem cartões para estudar agora.",
        flipPrompt: "Aperte Espaço para ver a resposta",
        graded: (label, interval) => `Avaliado: ${label} — próxima revisão em ${interval}.`,
        gradeLabels: { 1: "Repetir", 2: "Difícil", 3: "Bom", 4: "Fácil" },
      }
    : {
        export: "Export",
        noDecks: "No decks yet.",
        newTag: "New",
        reviewTag: "Review",
        hintFlip: "Space to flip · 1–4 to grade",
        done: "All caught up — no cards to study right now.",
        flipPrompt: "Press Space to reveal the answer",
        graded: (label, interval) =>
          `Graded ${label} — next review in ${formatInterval(interval)}.`,
        gradeLabels: { 1: "Again", 2: "Hard", 3: "Good", 4: "Easy" },
      };

  const cardEl = h("div", { class: "srs-card", tabindex: "0" });
  const controlsEl = h("div", { class: "srs-controls" });
  const progressEl = h("p", { class: "muted" });
  const statusEl = h("p", { class: "srs-status", "aria-live": "polite" });
  const exportBtn = h("button", {
    type: "button",
    class: "chip",
    text: ui.export,
    onclick: exportData,
  });

  function localGradeLabel(grade) {
    return ui.gradeLabels[grade] || gradeLabel(grade);
  }

  function render() {
    clear(cardEl);
    clear(controlsEl);
    const card = cards[index];
    if (!card) return;

    cardEl.append(
      h(
        "div",
        { class: "srs-front-row" },
        h("p", { class: "srs-front", text: card.front }),
        pronounceButton(card.front, "🔊", lang),
        h("span", { class: "tag", text: card.repetitions === 0 ? ui.newTag : ui.reviewTag }),
      ),
      flipped
        ? h(
            "div",
            { class: "srs-back" },
            h("p", { class: "srs-def", text: card.back }),
            card.l1_hint ? h("p", { class: "es-note", text: `🇪🇸 ${card.l1_hint}` }) : null,
            card.ipa ? h("p", { class: "wod-ipa", text: card.ipa }) : null,
            h(
              "ul",
              { class: "wod-examples" },
              card.examples.map((example) => h("li", { text: example })),
            ),
          )
        : h("p", { class: "muted", text: ui.flipPrompt }),
    );

    progressEl.textContent = `${index + 1} / ${cards.length}`;

    if (flipped) {
      for (let grade = 1; grade <= 4; grade += 1) {
        controlsEl.append(
          h("button", {
            class: "grade",
            type: "button",
            onclick: () => gradeCard(grade),
            text: `${grade} · ${localGradeLabel(grade)}`,
          }),
        );
      }
    }
  }

  async function gradeCard(grade) {
    const card = cards[index];
    if (!card || !flipped || busy) return;
    busy = true;
    try {
      const result = await apiPost("/api/srs/review", { card_id: card.id, grade });
      statusEl.textContent = ui.graded(localGradeLabel(grade), result.interval_days);
      cards.splice(index, 1);
      if (index >= cards.length) index = 0;
      flipped = false;
      if (cards.length) render();
      else {
        clear(cardEl);
        clear(controlsEl);
        progressEl.textContent = "";
        cardEl.append(h("p", { class: "muted", text: ui.done }));
      }
    } catch (error) {
      statusEl.textContent = error.message;
    } finally {
      busy = false;
    }
  }

  function onKey(event) {
    if (isInteractive(event.target)) return;
    if (event.code === "Space") {
      if (!cards.length) return;
      event.preventDefault();
      flipped = !flipped;
      render();
    } else if (["1", "2", "3", "4"].includes(event.key) && flipped) {
      event.preventDefault();
      gradeCard(Number(event.key));
    }
  }

  async function exportData() {
    try {
      const data = await apiGet("/api/srs/export");
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const anchor = h("a", { href: url, download: "logos-workspace-srs-export.json" });
      document.body.append(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      statusEl.textContent = error.message;
    }
  }

  async function load() {
    try {
      const decks = await apiGet(`/api/srs/decks?cockpit=${cockpit}`);
      clear(slot);
      if (!decks.length) {
        slot.append(h("p", { class: "muted", text: ui.noDecks }));
        return;
      }
      const deckId = decks[0].id;
      const [newCards, dueCards] = await Promise.all([
        apiGet(`/api/srs/decks/${deckId}/new`),
        apiGet(`/api/srs/decks/${deckId}/due`),
      ]);
      cards = [...newCards, ...dueCards];
      slot.append(
        cardEl,
        controlsEl,
        progressEl,
        statusEl,
        h("p", { class: "muted", text: ui.hintFlip }),
        h("div", { class: "chips" }, exportBtn),
      );
      if (cards.length) render();
      else cardEl.append(h("p", { class: "muted", text: ui.done }));
    } catch (error) {
      clear(slot);
      slot.append(h("p", { class: "error", text: `SRS unavailable: ${error.message}` }));
    }
  }

  // Scope flashcard keyboard to this module's card (and its slot when it is
  // moved into the dialog). A global document listener would flip cards or
  // grade from any view and would not stop when the card is out of context.
  slot.addEventListener("keydown", onKey);
  load();
}

function isInteractive(target) {
  if (!(target instanceof HTMLElement)) return false;
  return target.closest("button, a, input, textarea, select, [contenteditable]") !== null;
}

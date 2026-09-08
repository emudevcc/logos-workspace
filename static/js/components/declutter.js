// Writing Coach: polish (de-clutter) and correct a draft.

import { apiPost } from "../lib/api.js";
import { clear, h } from "../lib/dom.js";
import { reductionPercent } from "../lib/text.js";

/**
 * @param {HTMLElement} slot
 */
export function init(slot) {
  const textarea = h("textarea", {
    class: "declutter-input",
    rows: "6",
    placeholder: "Paste an email or chat draft…",
    "aria-label": "Draft to improve",
  });
  const polishBtn = h("button", { class: "primary", type: "button", text: "Polish", onclick: polish });
  const correctBtn = h("button", { class: "primary", type: "button", text: "Correct", onclick: correct });
  const resultEl = h("div", { class: "declutter-result", "aria-live": "polite" });

  slot.append(
    textarea,
    h("div", { class: "chips" }, polishBtn, correctBtn),
    h("p", { class: "muted", text: "Polish tightens style · Correct fixes grammar mistakes" }),
    resultEl,
  );

  async function polish() {
    const draft = textarea.value.trim();
    if (!draft) return;
    polishBtn.disabled = true;
    clear(resultEl);
    resultEl.append(h("p", { class: "muted", text: "Polishing…" }));
    try {
      const data = await apiPost("/api/declutter", { draft });
      renderPolishResult(resultEl, data);
    } catch (error) {
      clear(resultEl);
      resultEl.append(h("p", { class: "error", text: `Polish failed: ${error.message}` }));
    } finally {
      polishBtn.disabled = false;
    }
  }

  async function correct() {
    const draft = textarea.value.trim();
    if (!draft) return;
    correctBtn.disabled = true;
    clear(resultEl);
    resultEl.append(h("p", { class: "muted", text: "Checking…" }));
    try {
      const data = await apiPost("/api/writing/correct", { draft });
      renderCorrectResult(resultEl, data);
    } catch (error) {
      clear(resultEl);
      resultEl.append(h("p", { class: "error", text: `Correct failed: ${error.message}` }));
    } finally {
      correctBtn.disabled = false;
    }
  }
}

function renderPolishResult(resultEl, data) {
  clear(resultEl);
  const before = data.word_count_before;
  const after = data.word_count_after;
  const copyBtn = h("button", {
    type: "button",
    class: "chip",
    text: "Copy revised",
    onclick: () => copyText(data.revised, copyBtn),
  });
  resultEl.append(
    h("p", { class: "declutter-meta", text: `Word count: ${before} → ${after} (−${reductionPercent(before, after)}%)` }),
    h("div", { class: "bluf" }, h("strong", { text: "Revised: " }), data.revised),
  );
  if (data.verb_upgrades.length) {
    const list = h("ul", { class: "upgrade-list" });
    for (const upgrade of data.verb_upgrades) {
      list.append(h("li", { text: `${upgrade.weak} → ${upgrade.strong}` }));
    }
    resultEl.append(h("p", { class: "subtitle", text: "Weak → strong verbs" }), list);
  }
  resultEl.append(h("p", { class: "tone", text: `Tone: ${data.tone_assessment}` }));
  resultEl.append(h("div", { class: "chips" }, copyBtn));
}

function renderCorrectResult(resultEl, data) {
  clear(resultEl);
  const copyBtn = h("button", {
    type: "button",
    class: "chip",
    text: "Copy corrected",
    onclick: () => copyText(data.corrected, copyBtn),
  });
  resultEl.append(
    h("div", { class: "bluf" }, h("strong", { text: "Corrected: " }), data.corrected),
  );
  if (data.error_count) {
    const list = h("ul", { class: "upgrade-list" });
    for (const correction of data.corrections) {
      list.append(
        h("li", { text: `${correction.original} → ${correction.corrected} — ${correction.explanation}` }),
      );
    }
    resultEl.append(
      h("p", { class: "subtitle", text: `${data.error_count} correction${data.error_count === 1 ? "" : "s"}` }),
      list,
    );
  } else {
    resultEl.append(h("p", { class: "quiz-correct", text: "✓ No errors found" }));
  }
  resultEl.append(h("div", { class: "chips" }, copyBtn));
}

function copyText(text, button) {
  if (!navigator.clipboard) {
    button.textContent = "Copy unavailable";
    return;
  }
  navigator.clipboard.writeText(text).then(
    () => {
      button.textContent = "Copied ✓";
    },
    () => {
      button.textContent = "Copy failed";
    },
  );
}

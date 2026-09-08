// Verbs & Grammar hub: irregular verbs, phrasal verbs, collocations,
// use of English, word forms, rule of the day, and a free-form grammar coach.

import { apiGet, apiPost } from "../lib/api.js";
import { checkIrregularVerb, pickNoRepeat, sameAnswer } from "../lib/drill.js";
import { clear, h } from "../lib/dom.js";
import { pronounce } from "../lib/pronounce.js";
import { subscribeIdleRefresh } from "../lib/view_refresh.js";

const TABS = [
  { id: "verbs", label: "Irregular Verbs" },
  { id: "phrasal", label: "Phrasal Verbs" },
  { id: "collocations", label: "Collocations" },
  { id: "use-of-english", label: "Use of English" },
  { id: "word-forms", label: "Word Forms" },
  { id: "rule", label: "Rule of the Day" },
  { id: "coach", label: "Grammar Coach" },
];

const KIND_HINTS = {
  phrasal_verb: "Choose the phrasal verb that fits the gap.",
  collocation: "Choose the word that collocates with the sentence.",
  use_of_english: "Choose the word that best fits the gap.",
};

let verbsCache = null;
let activeGeneration = 0;

/**
 * @param {HTMLElement} slot
 * @param {{bus?: {on: Function}}} [ctx]
 */
export function init(slot, ctx = {}) {
  const content = h("div", { class: "module-content" });
  let active = "verbs";
  // Idle-advance callback for the *currently rendered* drill, refreshed by the
  // content cycle: re-rolls the visible prompt only when the learner has not
  // started answering it (no typed input, no result, no in-flight request).
  let rotateIdle = null;
  subscribeIdleRefresh(slot, ctx, () => rotateIdle);

  const tabButtons = TABS.map((tab) =>
    h("button", {
      class: "tab",
      type: "button",
      text: tab.label,
      onclick: () => select(tab.id),
    }),
  );

  slot.append(h("div", { class: "tabs tabs-box" }, tabButtons), content);

  function select(id) {
    active = id;
    tabButtons.forEach((button, index) => {
      button.classList.toggle("tab-active", TABS[index].id === id);
    });
    activeGeneration += 1;
    render(activeGeneration);
  }

  function render(gen) {
    clear(content);
    rotateIdle = null;
    if (active === "verbs") rotateIdle = renderIrregular(content, gen);
    else if (active === "phrasal") rotateIdle = renderCloze(content, "phrasal_verb", gen);
    else if (active === "collocations") rotateIdle = renderCloze(content, "collocation", gen);
    else if (active === "use-of-english") rotateIdle = renderCloze(content, "use_of_english", gen);
    else if (active === "word-forms") rotateIdle = renderWordForms(content, gen);
    else if (active === "rule") renderRule(content, gen);
    else renderCoach(content);
  }

  select("verbs");
}

function renderIrregular(slot, gen) {
  const verbEl = h("div", { class: "drill-verb" });
  const pastInput = h("input", {
    class: "declutter-input",
    placeholder: "Past simple",
    "aria-label": "Past simple",
  });
  const participleInput = h("input", {
    class: "declutter-input",
    placeholder: "Past participle",
    "aria-label": "Past participle",
  });
  const checkBtn = h("button", { class: "primary", type: "button", text: "Check", onclick: check });
  const nextBtn = h("button", { class: "chip", type: "button", text: "Next", onclick: next });
  const resultEl = h("div", { class: "drill-result", "aria-live": "polite" });

  slot.append(
    h("p", { class: "muted", text: "Type the past simple and past participle." }),
    verbEl,
    pastInput,
    participleInput,
    h("div", { class: "chips" }, checkBtn, nextBtn),
    resultEl,
  );

  let current = null;
  // Cycle through the whole pool before allowing a verb to repeat, so Next
  // never feels like it is walking a fixed (or repeated) order. The verb shown
  // on the previous page load is pre-marked as seen so a reload starts on
  // something different.
  const seenVerbs = new Set(readLastVerb() ? [readLastVerb()] : []);

  function next() {
    if (!verbsCache || !verbsCache.length) return;
    current = pickNoRepeat(verbsCache, seenVerbs, (verb) => verb.base);
    writeLastVerb(current.base);
    clear(verbEl);
    verbEl.append(
      h("span", { class: "wod-term", text: current.base }),
      h("button", {
        class: "chip",
        type: "button",
        "aria-label": "Pronounce",
        title: "Pronounce",
        text: "Play",
        onclick: () => pronounce(current.base),
      }),
    );
    pastInput.value = "";
    participleInput.value = "";
    clear(resultEl);
    pastInput.focus();
  }

  function check() {
    if (!current) return;
    const result = checkIrregularVerb(current, pastInput.value, participleInput.value);
    clear(resultEl);
    if (result.pastCorrect && result.participleCorrect) {
      resultEl.append(h("p", { class: "quiz-correct", text: "✓ Correct" }));
    } else {
      const saveBtn = h("button", {
        class: "chip",
        type: "button",
        text: "＋ Save to review",
        onclick: () => saveCard(`${current.base} (past / participle)`, `${current.past} / ${current.participle}`, saveBtn),
      });
      resultEl.append(
        h("p", { class: "quiz-wrong", text: `✗ ${current.base} → ${current.past} / ${current.participle}` }),
        h("div", { class: "chips" }, saveBtn),
      );
    }
  }

  if (verbsCache) {
    next();
  } else {
    verbEl.append(h("span", { class: "muted", text: "Loading…" }));
    apiGet("/api/grammar/irregular-verbs")
      .then((verbs) => {
        if (gen !== activeGeneration) return;
        verbsCache = verbs;
        next();
      })
      .catch((error) => {
        if (gen !== activeGeneration) return;
        clear(verbEl);
        verbEl.append(h("span", { class: "error", text: `Unavailable: ${error.message}` }));
      });
  }

  return () => {
    // Never steal a half-typed answer or an on-screen result.
    if (pastInput.value || participleInput.value || resultEl.childElementCount) return;
    next();
  };
}

function renderCloze(slot, kind, gen) {
  const questionEl = h("div", {});
  const nextBtn = h("button", { class: "chip", type: "button", text: "Next", onclick: load });
  const statusEl = h("div", { class: "drill-result", "aria-live": "polite" });

  slot.append(
    h("p", { class: "muted", text: KIND_HINTS[kind] }),
    questionEl,
    h("div", { class: "chips" }, nextBtn),
    statusEl,
  );

  let optionButtons = [];
  let loading = false;

  async function load() {
    if (loading) return;
    loading = true;
    clear(questionEl);
    clear(statusEl);
    optionButtons = [];
    questionEl.append(h("p", { class: "muted", text: "Loading…" }));
    try {
      const drill = await apiGet(`/api/grammar/drill?kind=${kind}`);
      if (gen !== activeGeneration) return;
      clear(questionEl);
      questionEl.append(h("p", { class: "shadow-target", text: drill.sentence }));
      const optionsEl = h("div", { class: "chips" });
      for (const option of drill.options) {
        const btn = h("button", {
          class: "chip",
          type: "button",
          text: option,
          onclick: () => answer(option, drill),
        });
        optionButtons.push(btn);
        optionsEl.append(btn);
      }
      questionEl.append(optionsEl);
    } catch (error) {
      if (gen !== activeGeneration) return;
      clear(questionEl);
      questionEl.append(h("p", { class: "error", text: `Drill unavailable: ${error.message}` }));
    } finally {
      loading = false;
    }
  }

  function answer(choice, drill) {
    for (const button of optionButtons) button.disabled = true;
    const correct = sameAnswer(choice, drill.answer);
    clear(statusEl);
    if (correct) {
      statusEl.append(h("p", { class: "quiz-correct", text: "✓ Correct" }));
    } else {
      const saveBtn = h("button", {
        class: "chip",
        type: "button",
        text: "＋ Save to review",
        onclick: () => saveCard(drill.sentence, drill.answer, saveBtn),
      });
      statusEl.append(
        h("p", { class: "quiz-wrong", text: `✗ Correct: ${drill.answer}` }),
        h("div", { class: "chips" }, saveBtn),
      );
    }
    if (drill.explanation) statusEl.append(h("p", { class: "muted", text: drill.explanation }));
  }

  load();

  return () => {
    // Only re-roll an unanswered, pristine prompt (no in-flight fetch, and no
    // option locked in by an answer yet).
    if (loading) return;
    if (optionButtons.some((button) => button.disabled)) return;
    load();
  };
}

function renderWordForms(slot, gen) {
  const questionEl = h("div", {});
  const input = h("input", {
    class: "declutter-input",
    placeholder: "Type the correct form",
    "aria-label": "Answer",
  });
  const checkBtn = h("button", { class: "primary", type: "button", text: "Check", onclick: check });
  const nextBtn = h("button", { class: "chip", type: "button", text: "Next", onclick: load });
  const statusEl = h("div", { class: "drill-result", "aria-live": "polite" });

  slot.append(questionEl, input, h("div", { class: "chips" }, checkBtn, nextBtn), statusEl);

  let drill = null;
  let loading = false;

  async function load() {
    if (loading) return;
    loading = true;
    clear(questionEl);
    clear(statusEl);
    input.value = "";
    drill = null;
    questionEl.append(h("p", { class: "muted", text: "Loading…" }));
    try {
      drill = await apiGet("/api/grammar/word-forms");
      if (gen !== activeGeneration) return;
      clear(questionEl);
      questionEl.append(
        h("p", { class: "shadow-target", text: drill.sentence }),
        h("p", { class: "muted", text: `Root word: ${drill.root}` }),
      );
      input.focus();
    } catch (error) {
      if (gen !== activeGeneration) return;
      clear(questionEl);
      questionEl.append(h("p", { class: "error", text: `Drill unavailable: ${error.message}` }));
    } finally {
      loading = false;
    }
  }

  function check() {
    if (!drill) return;
    const ok = sameAnswer(input.value, drill.answer);
    clear(statusEl);
    if (ok) {
      statusEl.append(h("p", { class: "quiz-correct", text: "✓ Correct" }));
    } else {
      const saveBtn = h("button", {
        class: "chip",
        type: "button",
        text: "＋ Save to review",
        onclick: () => saveCard(`${drill.root} → ${drill.answer}`, drill.sentence, saveBtn),
      });
      statusEl.append(
        h("p", { class: "quiz-wrong", text: `✗ Correct: ${drill.answer}` }),
        h("div", { class: "chips" }, saveBtn),
      );
    }
    if (drill.explanation) statusEl.append(h("p", { class: "muted", text: drill.explanation }));
  }

  load();

  return () => {
    // Re-roll only an untouched prompt (no typed word, no result, no fetch).
    if (loading) return;
    if (input.value || statusEl.childElementCount) return;
    load();
  };
}

async function renderRule(slot, gen) {
  slot.append(h("p", { class: "muted", text: "Loading…" }));
  try {
    const rule = await apiGet("/api/grammar/rule-of-day");
    if (gen !== activeGeneration) return;
    clear(slot);
    const examples = h("ul", { class: "wod-examples" });
    for (const example of rule.examples) examples.append(h("li", { text: example }));
    slot.append(
      h("h3", { class: "quiz-question", text: rule.title }),
      h("p", { text: rule.rule }),
      examples,
      h("p", { class: "error", text: `⚠ Common mistake: ${rule.common_error}` }),
    );
  } catch (error) {
    if (gen !== activeGeneration) return;
    clear(slot);
    slot.append(h("p", { class: "error", text: `Rule unavailable: ${error.message}` }));
  }
}

function renderCoach(slot) {
  const input = h("textarea", {
    class: "declutter-input",
    rows: "3",
    placeholder: "Ask a grammar question…",
    "aria-label": "Grammar question",
  });
  const button = h("button", { class: "primary", type: "button", text: "Ask", onclick: ask });
  const resultEl = h("div", { class: "declutter-result", "aria-live": "polite" });

  slot.append(input, button, resultEl);

  async function ask() {
    const question = input.value.trim();
    if (!question) return;
    button.disabled = true;
    clear(resultEl);
    resultEl.append(h("p", { class: "muted", text: "Thinking…" }));
    try {
      const data = await apiPost("/api/grammar/coach", { question });
      clear(resultEl);
      resultEl.append(h("div", { class: "bluf" }, data.answer));
    } catch (error) {
      clear(resultEl);
      resultEl.append(h("p", { class: "error", text: error.message }));
    } finally {
      button.disabled = false;
    }
  }
}

async function saveCard(front, back, button) {
  try {
    await apiPost("/api/srs/cards", { front, back, register_tag: "Grammar" });
    button.textContent = "Saved ✓";
    button.disabled = true;
  } catch {
    button.textContent = "Save failed";
  }
}

const LAST_VERB_KEY = "cockpit-last-verb-base";

function readLastVerb() {
  try {
    return localStorage.getItem(LAST_VERB_KEY) || "";
  } catch {
    return "";
  }
}

function writeLastVerb(base) {
  try {
    localStorage.setItem(LAST_VERB_KEY, base);
  } catch {
    /* storage unavailable */
  }
}

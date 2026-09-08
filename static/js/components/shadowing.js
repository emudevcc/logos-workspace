// Pronunciation practice: Shadowing, Minimal Pairs, and Dictation.

import { apiGet } from "../lib/api.js";
import { clear, h } from "../lib/dom.js";
import { pickNoRepeat } from "../lib/drill.js";
import { pronounce } from "../lib/pronounce.js";
import { shadowDiff } from "../lib/shadow.js";
import { subscribeIdleRefresh } from "../lib/view_refresh.js";

const SENTENCES = [
  "We need to align on the roadmap before the kickoff.",
  "Could you walk me through the incident timeline?",
  "Let's circle back once the quarterly numbers come in.",
  "The proposal tries to boil the ocean and misses the point.",
  "I don't have the bandwidth for another project this sprint.",
  "We should tackle the low-hanging fruit before the redesign.",
];

const LAST_PAIR_KEY = "cockpit-last-pair";

function readLastPair() {
  try {
    return localStorage.getItem(LAST_PAIR_KEY) || "";
  } catch {
    return "";
  }
}

function writeLastPair(key) {
  try {
    localStorage.setItem(LAST_PAIR_KEY, key);
  } catch {
    /* storage unavailable */
  }
}

// Fetch a fresh random sentence from the LLM; fall back to the starter pool if
// unavailable so shadowing/dictation always have something to practice.
async function fetchFreshSentence() {
  try {
    const data = await apiGet("/api/pronunciation/sentence");
    if (data && typeof data.sentence === "string" && data.sentence.trim()) {
      return data.sentence;
    }
  } catch {
    /* fall through to the local pool */
  }
  return SENTENCES[Math.floor(Math.random() * SENTENCES.length)];
}

const TABS = [
  { id: "shadow", label: "Shadow" },
  { id: "pairs", label: "Minimal Pairs" },
  { id: "dictation", label: "Dictation" },
];

/**
 * @param {HTMLElement} slot
 * @param {{bus?: {on: Function}}} [ctx]
 */
export function init(slot, ctx = {}) {
  const content = h("div", { class: "module-content" });
  let active = "shadow";
  let gen = 0;
  // Idle-advance callback for the visible tab; the content-refresh cycle calls
  // it to rotate a stale sentence/pair only when the learner is not mid-answer.
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
    gen += 1;
    render(gen);
  }

  // register sets rotateIdle only for the render it belongs to, so an async
  // tab render finishing after a tab switch cannot hijack the refresh hook.
  function render(token) {
    clear(content);
    rotateIdle = null;
    const register = (fn) => {
      if (token === gen) rotateIdle = fn;
    };
    if (active === "shadow") renderShadow(content, register);
    else if (active === "pairs") renderPairs(content, register);
    else renderDictation(content, register);
  }

  select("shadow");
}

function renderShadow(slot, register) {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  // The opening sentence is fetched fresh from the LLM (never one of the fixed
  // starter phrases), so a reload always shows new content. The local pool is
  // only a fallback when the LLM is unreachable.
  let target = "";

  const targetEl = h("p", { class: "shadow-target", text: "Loading a fresh sentence…" });
  const playBtn = h("button", { class: "chip", type: "button", text: "Play", onclick: () => pronounce(target) });
  const nextBtn = h("button", { class: "chip", type: "button", text: "Next", onclick: nextSentence });
  const recBtn = h("button", { class: "primary", type: "button", "aria-pressed": "false", onclick: toggleRecord });
  const recLabel = h("span");

  function setArmed(armed) {
    recBtn.classList.toggle("is-live", armed);
    recBtn.setAttribute("aria-pressed", String(armed));
    recLabel.textContent = armed ? "Stop" : "Record";
  }
  setArmed(false);
  recBtn.append(recLabel);
  const resultEl = h("div", { class: "shadow-result", "aria-live": "polite" });

  slot.append(targetEl, h("div", { class: "chips" }, playBtn, nextBtn, recBtn), resultEl);

  let recognition = null;
  let finalTranscript = "";

  async function nextSentence() {
    target = await fetchFreshSentence();
    targetEl.textContent = target;
    clear(resultEl);
  }

  if (Recognition) {
    recognition = new Recognition();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.continuous = false;
    recognition.onresult = (event) => {
      finalTranscript = Array.from(event.results)
        .map((result) => result[0].transcript)
        .join(" ");
    };
    recognition.onend = () => {
      setArmed(false);
      if (finalTranscript.trim()) showDiff(finalTranscript.trim());
      finalTranscript = "";
    };
    recognition.onerror = () => {
      setArmed(false);
    };
  } else {
    recBtn.disabled = true;
    recBtn.textContent = "Speech not supported";
  }

  function toggleRecord() {
    if (!recognition) return;
    const live = recBtn.getAttribute("aria-pressed") === "true";
    if (!live) {
      try {
        recognition.start();
        setArmed(true);
      } catch {
        setArmed(false);
      }
    } else {
      recognition.stop();
    }
  }

  function showDiff(spoken) {
    const diff = shadowDiff(target, spoken);
    clear(resultEl);
    const line = h("p", { class: "shadow-line" });
    for (const item of diff.words) {
      line.append(h("span", { class: item.matched ? "shadow-hit" : "shadow-miss", text: item.word }), " ");
    }
    resultEl.append(
      h("p", { class: "shadow-score", text: `Accuracy: ${diff.accuracy}% (${diff.matched}/${diff.total} words)` }),
      line,
      h("p", { class: "muted", text: `You said: "${spoken}"` }),
    );
  }

  register(() => {
    // Never interrupt a live recording or erase an on-screen accuracy diff.
    if (recBtn.getAttribute("aria-pressed") === "true") return;
    if (resultEl.childElementCount) return;
    nextSentence();
  });

  // Opening sentence: fetch a fresh LLM sentence so every page load shows
  // something new (the fallback pool is used only when the LLM is unreachable).
  nextSentence();
}

async function renderPairs(slot, register) {
  let pairs = [];
  let currentPair = null;
  let currentWord = null;

  const promptEl = h("p", { class: "shadow-target", text: "Click Play, then choose which word you heard." });
  const playBtn = h("button", { class: "primary", type: "button", text: "Play", onclick: play });
  const optionsEl = h("div", { class: "chips" });
  const resultEl = h("div", { class: "drill-result", "aria-live": "polite" });

  slot.append(promptEl, playBtn, optionsEl, resultEl);

  try {
    pairs = await apiGet("/api/pronunciation/minimal-pairs");
    nextPair();
  } catch (error) {
    slot.append(h("p", { class: "error", text: error.message }));
    return;
  }

  try {
    const pitfalls = await apiGet("/api/pronunciation/pitfalls");
    const list = h("ul", { class: "wod-examples" });
    for (const pitfall of pitfalls) {
      list.append(h("li", { text: `${pitfall.issue}: ${pitfall.tip}` }));
    }
    slot.append(h("p", { class: "subtitle", text: "Spanish speaker pitfalls" }), list);
  } catch {
    /* pitfalls optional */
  }

  // Walk the whole pair list before repeating a pair, so Next never replays a
  // recent contrast while unseen ones remain. The pair shown on the previous
  // page load is pre-marked as seen so a reload starts on a different contrast.
  const seenPairs = new Set(readLastPair() ? [readLastPair()] : []);

  function nextPair() {
    if (!pairs.length) return;
    currentPair = pickNoRepeat(pairs, seenPairs, (pair) => `${pair.a}|${pair.b}`);
    writeLastPair(`${currentPair.a}|${currentPair.b}`);
    currentWord = Math.random() < 0.5 ? currentPair.a : currentPair.b;
    clear(optionsEl);
    clear(resultEl);
    optionsEl.append(
      h("button", { class: "chip", type: "button", text: currentPair.a, onclick: () => answer(currentPair.a) }),
      h("button", { class: "chip", type: "button", text: currentPair.b, onclick: () => answer(currentPair.b) }),
    );
  }

  function play() {
    pronounce(currentWord);
  }

  function answer(choice) {
    const correct = choice === currentWord;
    clear(resultEl);
    resultEl.append(
      h("p", { class: correct ? "quiz-correct" : "quiz-wrong", text: correct ? "✓ Correct" : `✗ You heard "${currentWord}"` }),
      h("p", { class: "muted", text: `${currentPair.a} ${currentPair.ipa_a} · ${currentPair.b} ${currentPair.ipa_b}` }),
      h("button", { class: "chip", type: "button", text: "Next", onclick: nextPair }),
    );
  }

  register(() => {
    // Wait for the pair list to load; never steal an unanswered prompt that
    // already shows a result (the learner just heard it).
    if (!currentPair || resultEl.childElementCount) return;
    nextPair();
  });
}

function renderDictation(slot, register) {
  // Also start from a fresh LLM sentence (local pool only as fallback).
  let target = "";

  const promptEl = h("p", { class: "shadow-target", text: "Loading a fresh sentence, then click Play…" });
  const playBtn = h("button", { class: "chip", type: "button", text: "Play", onclick: () => pronounce(target) });
  const nextBtn = h("button", { class: "chip", type: "button", text: "Next", onclick: nextSentence });
  const input = h("textarea", {
    class: "declutter-input",
    rows: "2",
    placeholder: "Type what you hear…",
    "aria-label": "Dictation answer",
  });
  const checkBtn = h("button", { class: "primary", type: "button", text: "Check", onclick: check });
  const resultEl = h("div", { class: "drill-result", "aria-live": "polite" });

  slot.append(promptEl, h("div", { class: "chips" }, playBtn, nextBtn), input, h("div", { class: "chips" }, checkBtn), resultEl);

  async function nextSentence() {
    target = await fetchFreshSentence();
    promptEl.textContent = "Click Play, then type what you hear.";
    input.value = "";
    clear(resultEl);
  }

  function check() {
    const diff = shadowDiff(target, input.value);
    clear(resultEl);
    const line = h("p", { class: "shadow-line" });
    for (const item of diff.words) {
      line.append(h("span", { class: item.matched ? "shadow-hit" : "shadow-miss", text: item.word }), " ");
    }
    resultEl.append(
      h("p", { class: "shadow-score", text: `Accuracy: ${diff.accuracy}% (${diff.matched}/${diff.total} words)` }),
      line,
      h("p", { class: "muted", text: target }),
    );
  }

  register(() => {
    // Never wipe a half-typed dictation or an on-screen score.
    if (input.value || resultEl.childElementCount) return;
    nextSentence();
  });

  nextSentence();
}

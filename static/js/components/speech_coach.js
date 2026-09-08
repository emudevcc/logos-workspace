// Live Speech & Speech-Metrics Coach: WPM/pace/fillers HUD + monologue drill.

import { apiGet, apiPost } from "../lib/api.js";
import { clear, h } from "../lib/dom.js";
import {
  cadenceLabel,
  countFillers,
  fillerRate,
  paceLabel,
  wordsPerMinute,
} from "../lib/speech.js";
import { countWords } from "../lib/text.js";

const TABS = [
  { id: "metrics", label: "Live Metrics" },
  { id: "monologue", label: "Monologue" },
];

/**
 * @param {HTMLElement} slot
 */
export function init(slot) {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Recognition) {
    slot.append(h("p", { class: "error", text: "Speech recognition is not supported in this browser." }));
    return;
  }

  const recognition = new Recognition();
  recognition.lang = "en-US";
  recognition.interimResults = true;
  recognition.continuous = true;

  const content = h("div", { class: "module-content" });
  let active = "metrics";

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
    recognition.onresult = null;
    recognition.onend = null;
    recognition.onerror = null;
    try {
      recognition.stop();
    } catch {
      /* not recording */
    }
    render();
  }

  function render() {
    clear(content);
    if (active === "metrics") renderMetrics(content, recognition);
    else renderMonologue(content, recognition);
  }

  select("metrics");
}

function renderMetrics(slot, recognition) {
  const wpmEl = h("span", { class: "hud-value", text: "0" });
  const paceEl = h("span", { class: "hud-label", text: "—" });
  const fillersEl = h("span", { class: "hud-value", text: "0" });
  const fillerRateEl = h("span", { class: "hud-label", text: "0/min" });
  const cadenceEl = h("span", { class: "hud-value", text: "—" });
  const startBtn = h("button", { class: "primary", type: "button", text: "Start listening", onclick: start });
  const stopBtn = h("button", { type: "button", text: "Stop", onclick: stop, disabled: true });
  const summaryEl = h("p", { class: "muted", "aria-live": "polite" });
  const transcriptEl = h("div", { class: "speech-transcript", "aria-live": "polite" });

  slot.append(
    h(
      "div",
      { class: "hud" },
      h("div", { class: "hud-cell" }, h("span", { class: "hud-label", text: "WPM" }), wpmEl, paceEl),
      h("div", { class: "hud-cell" }, h("span", { class: "hud-label", text: "Fillers" }), fillersEl, fillerRateEl),
      h("div", { class: "hud-cell" }, h("span", { class: "hud-label", text: "Cadence" }), cadenceEl),
    ),
    h("div", { class: "chips" }, startBtn, stopBtn),
    summaryEl,
    transcriptEl,
  );

  let startedAt = null;
  let transcript = "";

  recognition.onresult = (event) => {
    const results = Array.from(event.results);
    transcript = results.map((result) => result[0].transcript).join(" ");
    const words = countWords(transcript);
    const elapsed = startedAt ? (Date.now() - startedAt) / 1000 : 0;
    const wpm = wordsPerMinute(words, elapsed);
    const fillers = countFillers(transcript);
    const finalCount = results.filter((result) => result.isFinal).length;
    const cadence = finalCount ? Math.round(words / finalCount) : 0;

    wpmEl.textContent = String(wpm);
    paceEl.textContent = paceLabel(wpm);
    paceEl.dataset.pace = paceLabel(wpm);
    fillersEl.textContent = String(fillers);
    fillerRateEl.textContent = `${fillerRate(fillers, elapsed)}/min`;
    cadenceEl.textContent = cadenceLabel(cadence);

    const display = transcript.length > 3000 ? `…${transcript.slice(-3000)}` : transcript;
    clear(transcriptEl);
    transcriptEl.append(display);
  };

  function start() {
    transcript = "";
    startedAt = Date.now();
    clear(summaryEl);
    recognition.start();
    startBtn.disabled = true;
    stopBtn.disabled = false;
  }

  function stop() {
    recognition.stop();
    const words = countWords(transcript);
    const elapsed = startedAt ? (Date.now() - startedAt) / 1000 : 0;
    const wpm = wordsPerMinute(words, elapsed);
    const fillers = countFillers(transcript);
    summaryEl.textContent =
      `Session: ${words} words · ${wpm} WPM (${paceLabel(wpm)}) · ` +
      `${fillers} fillers (${fillerRate(fillers, elapsed)}/min) · ${formatDuration(elapsed)}`;
    resetControls();
  }

  function resetControls() {
    startBtn.disabled = false;
    stopBtn.disabled = true;
  }

  recognition.onend = resetControls;
  recognition.onerror = resetControls;
}

function renderMonologue(slot, recognition) {
  const topicEl = h("p", { class: "shadow-target" });
  const newTopicBtn = h("button", { class: "chip", type: "button", text: "New topic", onclick: pickTopic });
  const startBtn = h("button", { class: "primary", type: "button", text: "Start speaking", onclick: start });
  const stopBtn = h("button", { type: "button", text: "Stop", onclick: stop, disabled: true });
  const liveEl = h("p", { class: "muted", "aria-live": "polite" });
  const resultEl = h("div", { class: "declutter-result", "aria-live": "polite" });

  slot.append(
    h("p", { class: "muted", text: "Speak for 60–90 seconds on the topic, then stop for feedback." }),
    topicEl,
    h("div", { class: "chips" }, newTopicBtn, startBtn, stopBtn),
    liveEl,
    resultEl,
  );

  let topics = [];
  let topic = "";
  let transcript = "";
  let startedAt = null;

  async function loadTopics() {
    topicEl.textContent = "Loading topic…";
    try {
      topics = await apiGet("/api/speech/topics");
      pickTopic();
    } catch (error) {
      topicEl.textContent = `Topics unavailable: ${error.message}`;
    }
  }

  function pickTopic() {
    if (!topics.length) return;
    topic = topics[Math.floor(Math.random() * topics.length)];
    topicEl.textContent = topic;
    clear(resultEl);
  }

  recognition.onresult = (event) => {
    transcript = Array.from(event.results)
      .map((result) => result[0].transcript)
      .join(" ");
    const words = countWords(transcript);
    const elapsed = startedAt ? (Date.now() - startedAt) / 1000 : 0;
    liveEl.textContent = `${words} words · ${Math.round(elapsed)}s`;
  };

  function start() {
    transcript = "";
    startedAt = Date.now();
    clear(resultEl);
    recognition.start();
    startBtn.disabled = true;
    stopBtn.disabled = false;
  }

  function stop() {
    recognition.stop();
    stopBtn.disabled = true;
    startBtn.disabled = false;
  }

  recognition.onend = () => {
    startBtn.disabled = false;
    stopBtn.disabled = true;
    if (startedAt && transcript.trim()) evaluate();
  };
  recognition.onerror = () => {
    startBtn.disabled = false;
    stopBtn.disabled = true;
  };

  async function evaluate() {
    const elapsed = startedAt ? (Date.now() - startedAt) / 1000 : 0;
    liveEl.textContent = "Evaluating…";
    try {
      const data = await apiPost("/api/speech/monologue/evaluate", {
        topic,
        transcript,
        duration_seconds: elapsed,
      });
      clear(resultEl);
      resultEl.append(
        h("p", {
          class: "subtitle",
          text:
            `Scores — structure ${data.structure_score} · fluency ${data.fluency_score} · ` +
            `vocabulary ${data.vocabulary_score} · grammar ${data.grammar_score}`,
        }),
      );
      if (data.strengths.length) {
        resultEl.append(h("p", { class: "subtitle", text: "Strengths" }));
        resultEl.append(list(data.strengths));
      }
      if (data.improvements.length) {
        resultEl.append(h("p", { class: "subtitle", text: "To improve" }));
        resultEl.append(list(data.improvements));
      }
      if (data.model_answer) {
        resultEl.append(h("p", { class: "subtitle", text: "Model answer" }));
        resultEl.append(h("div", { class: "bluf" }, data.model_answer));
      }
    } catch (error) {
      clear(resultEl);
      resultEl.append(h("p", { class: "error", text: error.message }));
    } finally {
      liveEl.textContent = "";
    }
  }

  loadTopics();
}

function list(items) {
  const ul = h("ul", { class: "wod-examples" });
  for (const item of items) ul.append(h("li", { text: item }));
  return ul;
}

function formatDuration(sec) {
  const s = Math.max(0, Math.round(sec));
  return `${Math.floor(s / 60)}m ${s % 60}s`;
}

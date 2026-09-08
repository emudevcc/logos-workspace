// Rapid-Fire PREP Drill: 90-second countdown with auto-submit at 00:00.

import { apiGet, apiPost } from "../lib/api.js";
import { clear, h } from "../lib/dom.js";
import { formatClock, isExpired, remainingSeconds } from "../lib/timer.js";
import { subscribeIdleRefresh } from "../lib/view_refresh.js";

const DURATION_SECONDS = 90;

/**
 * @param {HTMLElement} slot
 * @param {{bus?: {on: Function}}} [ctx]
 */
export function init(slot, ctx = {}) {
  let scenario = null;
  let startedAt = null;
  let intervalId = null;
  let submitting = false;
  let uiReady = false;

  // Content refresh rotates a stale scenario only while the drill is pristine:
  // not started, no draft typed, and no previous round's feedback on screen.
  subscribeIdleRefresh(slot, ctx, () => {
    if (!uiReady || startedAt || textarea.value.trim() || feedbackEl.childElementCount) return null;
    return reset;
  });

  const scenarioEl = h("div", { class: "prep-scenario" });
  const timerEl = h("div", {
    class: "prep-timer",
    text: formatClock(DURATION_SECONDS),
    role: "timer",
    "aria-label": "Time remaining",
  });
  const startBtn = h("button", { class: "primary", type: "button", text: "Start 90s drill", onclick: start });
  const textarea = h("textarea", {
    class: "prep-input",
    rows: "6",
    placeholder: "Write your PREP response…",
    "aria-label": "PREP response",
  });
  const submitBtn = h("button", { class: "primary", type: "button", text: "Submit", onclick: submit });
  const feedbackEl = h("div", { class: "prep-feedback", "aria-live": "polite" });

  function start() {
    if (!scenario || startedAt) return;
    startedAt = Date.now();
    startBtn.disabled = true;
    textarea.disabled = false;
    textarea.focus();
    intervalId = setInterval(tick, 250);
  }

  function tick() {
    timerEl.textContent = formatClock(remainingSeconds(DURATION_SECONDS, startedAt, Date.now()));
    if (isExpired(DURATION_SECONDS, startedAt, Date.now())) submit();
  }

  async function submit() {
    if (!scenario || submitting) return;
    if (intervalId) clearInterval(intervalId);
    const response = textarea.value.trim();
    if (!response) {
      clear(feedbackEl);
      feedbackEl.append(h("p", { class: "error", text: "Nothing to submit." }));
      return;
    }
    const elapsed = startedAt
      ? Math.min(DURATION_SECONDS, Math.round((Date.now() - startedAt) / 1000))
      : DURATION_SECONDS;
    submitting = true;
    submitBtn.disabled = true;
    try {
      const result = await apiPost("/api/prep/evaluate", {
        scenario: `${scenario.context} ${scenario.task}`,
        response,
        elapsed_seconds: elapsed,
      });
      renderFeedback(result);
    } catch (error) {
      clear(feedbackEl);
      feedbackEl.append(h("p", { class: "error", text: `Evaluation failed: ${error.message}` }));
    } finally {
      submitting = false;
      submitBtn.disabled = false;
    }
  }

  function renderFeedback(result) {
    clear(feedbackEl);
    feedbackEl.append(
      h("h3", { class: "subtitle", text: "Feedback" }),
      h("p", { text: `Conciseness: ${result.conciseness_score}/100 — ${result.conciseness_feedback}` }),
      h("p", { text: `Structure: ${result.structure_score}/100 — ${result.structure_feedback}` }),
      h("div", { class: "bluf" }, h("strong", { text: "BLUF rewrite: " }), result.bluf_rewrite),
      h("p", { text: result.overall_feedback }),
      h("button", { class: "primary", type: "button", text: "Run again", onclick: reset }),
    );
  }

  async function reset() {
    if (intervalId) clearInterval(intervalId);
    intervalId = null;
    startedAt = null;
    submitting = false;
    textarea.value = "";
    startBtn.disabled = false;
    submitBtn.disabled = false;
    timerEl.textContent = formatClock(DURATION_SECONDS);
    clear(feedbackEl);
    try {
      scenario = await apiGet("/api/prep/scenario");
      clear(scenarioEl);
      scenarioEl.append(
        h("p", { class: "muted", text: scenario.context }),
        h("p", { class: "prep-task", text: scenario.task }),
      );
    } catch (error) {
      feedbackEl.append(h("p", { class: "error", text: `PREP unavailable: ${error.message}` }));
    }
  }

  (async () => {
    try {
      scenario = await apiGet("/api/prep/scenario");
      clear(slot);
      scenarioEl.append(
        h("p", { class: "muted", text: scenario.context }),
        h("p", { class: "prep-task", text: scenario.task }),
      );
      slot.append(scenarioEl, timerEl, startBtn, textarea, submitBtn, feedbackEl);
    } catch (error) {
      clear(slot);
      slot.append(h("p", { class: "error", text: `PREP unavailable: ${error.message}` }));
    } finally {
      uiReady = true;
    }
  })();
}

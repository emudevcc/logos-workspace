// Weekly Plan: generate a personalized seven-day study plan.

import { apiPost } from "../lib/api.js";
import { clear, h } from "../lib/dom.js";

const FOCUS_OPTIONS = ["Speaking", "Listening", "Vocabulary", "Grammar", "Writing", "Pronunciation"];
const STORAGE_KEY = "cockpit-weekly-plan";

/**
 * @param {HTMLElement} slot
 */
export function init(slot) {
  const goalInput = h("input", {
    class: "declutter-input",
    placeholder: "Goal (e.g. pass C1, present confidently)…",
    "aria-label": "Goal",
  });
  const minutesInput = h("input", {
    class: "declutter-input",
    type: "number",
    min: "5",
    max: "240",
    value: "30",
    "aria-label": "Minutes per day",
  });
  const focusEl = h("div", { class: "chips" });
  const selected = new Set(["Speaking"]);
  for (const focus of FOCUS_OPTIONS) {
    const chip = h("button", {
      class: "chip",
      type: "button",
      text: focus,
      onclick: () => toggle(chip, focus),
    });
    chip.classList.toggle("is-active", selected.has(focus));
    focusEl.append(chip);
  }
  const button = h("button", { class: "primary", type: "button", text: "Generate plan", onclick: generate });
  const resultEl = h("div", { class: "declutter-result", "aria-live": "polite" });

  slot.append(
    h("p", { class: "muted", text: "Goal" }),
    goalInput,
    h("p", { class: "muted", text: "Minutes per day" }),
    minutesInput,
    h("p", { class: "muted", text: "Focus areas" }),
    focusEl,
    h("div", { class: "chips" }, button),
    resultEl,
  );

  function toggle(chip, focus) {
    if (selected.has(focus)) {
      selected.delete(focus);
      chip.classList.remove("is-active");
    } else {
      selected.add(focus);
      chip.classList.add("is-active");
    }
  }

  async function generate() {
    const goal = goalInput.value.trim();
    if (!goal) return;
    const minutes = Math.max(5, Math.min(240, Number(minutesInput.value) || 30));
    button.disabled = true;
    clear(resultEl);
    resultEl.append(h("p", { class: "muted", text: "Building your week…" }));
    try {
      const data = await apiPost("/api/plan/weekly", {
        goal,
        minutes_per_day: minutes,
        focus_areas: [...selected],
      });
      render(data);
      persist({ goal, minutes, data });
    } catch (error) {
      clear(resultEl);
      resultEl.append(h("p", { class: "error", text: `Plan failed: ${error.message}` }));
    } finally {
      button.disabled = false;
    }
  }

  function render(data) {
    clear(resultEl);
    const listEl = h("ul", { class: "upgrade-list" });
    for (const day of data.days) {
      listEl.append(h("li", { text: `${day.day} — ${day.activity} (${day.duration_minutes} min)` }));
    }
    resultEl.append(listEl);
    if (data.tip) resultEl.append(h("p", { class: "tone", text: `Tip: ${data.tip}` }));
  }

  function persist(plan) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(plan));
    } catch {
      /* storage unavailable */
    }
  }

  function restore() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const saved = JSON.parse(raw);
      if (saved.goal) goalInput.value = saved.goal;
      if (saved.data) render(saved.data);
    } catch {
      /* ignore corrupt cache */
    }
  }

  restore();
}

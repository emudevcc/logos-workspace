// "Your next step" — surfaces the next action for a learning session.

import { apiGet } from "../lib/api.js";
import { getActiveCockpit } from "../lib/cockpit.js";
import { clear, h } from "../lib/dom.js";

/**
 * @param {HTMLElement} slot
 */
export function init(slot) {
  async function load() {
    try {
      const cockpit = getActiveCockpit(window.localStorage);
      const stats = await apiGet(`/api/srs/stats?cockpit=${cockpit}`);
      clear(slot);
      const due = stats.cards_due || 0;
      const done = stats.reviews_today || 0;
      const goal = stats.daily_goal || 20;
      slot.append(
        h("p", {
          class: "text-sm opacity-75",
          text: `${stats.streak_days || 0}-day streak · ${done}/${goal} reviews today`,
        }),
        h(
          "div",
          { class: "flex flex-wrap gap-2" },
          h("button", {
            class: "btn btn-primary btn-sm",
            type: "button",
            text: due ? `Review ${due} due card${due === 1 ? "" : "s"} →` : "Start a practice drill →",
            onclick: goPractice,
          }),
        ),
      );
    } catch {
      clear(slot);
      slot.append(h("p", { class: "text-sm opacity-75", text: "Could not load progress." }));
    }
  }

  function goPractice() {
    const nav = document.querySelector('[data-view="practice"]');
    if (nav) nav.click();
  }

  load();
}

// Progress / streak strip (header) with a daily-review goal ring, a persistent
// content-refresh countdown, and a force-refresh button.

import { apiGet } from "../lib/api.js";
import { clear, h } from "../lib/dom.js";
import { formatClock, isExpired, remainingSeconds } from "../lib/timer.js";

const STATS_REFRESH_MS = 60 * 1000;
const CONTENT_REFRESH_MS = 30 * 60 * 1000;
const CONTENT_REFRESH_SEC = CONTENT_REFRESH_MS / 1000;
const ANCHOR_KEY = "cockpit-content-refresh-anchor";

/**
 * @param {HTMLElement} el
 * @param {{bus?: {on: Function, emit: Function}}} [ctx]
 */
export function init(el, ctx = {}) {
  const bus = ctx.bus;

  // The anchor persists across reloads, so the countdown doesn't restart when
  // the page is refreshed. If the persisted cycle already elapsed (e.g. the
  // kiosk was off), start a fresh cycle — the modules fetch on boot anyway.
  let contentStart = readAnchor();
  if (isExpired(CONTENT_REFRESH_SEC, contentStart, Date.now())) {
    contentStart = Date.now();
    writeAnchor(contentStart);
  }

  const countdownEl = h("span", {
    class: "stat",
    title: "Next automatic content refresh (news / podcast / word-of-day)",
  });
  const refreshBtn = h("button", {
    type: "button",
    class: "chip icon",
    "aria-label": "Refresh content now",
    title: "Refresh content now",
    text: "⟳",
    onclick: forceRefresh,
  });

  async function load() {
    try {
      const s = await apiGet("/api/srs/stats");
      clear(el);
      render(s);
      el.append(refreshBtn, countdownEl);
    } catch {
      clear(el);
    }
  }

  function render(s) {
    const hour = new Date().getHours();
    const greeting = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
    const streakDays = s.streak_days;
    const goal = s.daily_goal || 20;
    const pct = goal ? Math.min(1, s.reviews_today / goal) : 0;

    // Note: never pass null into Element.append — it renders a literal "null"
    // text node. Filter the list instead.
    const items = [
      h("span", { class: "greeting", text: greeting }),
      streakDays ? h("span", { class: "stat streak", text: `${streakDays}-day streak` }) : null,
      goalRing(pct, s.reviews_today, goal),
      h("span", { class: "stat-stat", text: `${s.cards_due} due` }),
      h("span", { class: "stat-stat", text: `${s.cards_new} new` }),
    ];
    for (const item of items) {
      if (item) el.append(item);
    }
  }

  function tick() {
    const now = Date.now();
    if (isExpired(CONTENT_REFRESH_SEC, contentStart, now)) {
      contentStart = now;
      writeAnchor(now);
      bus?.emit("content:refresh");
    }
    countdownEl.textContent = formatClock(remainingSeconds(CONTENT_REFRESH_SEC, contentStart, now));
  }

  function forceRefresh() {
    contentStart = Date.now();
    writeAnchor(contentStart);
    bus?.emit("content:refresh");
    tick();
  }

  load();
  tick();
  setInterval(load, STATS_REFRESH_MS);
  setInterval(tick, 1000);
}

function readAnchor() {
  try {
    const raw = localStorage.getItem(ANCHOR_KEY);
    const value = Number(raw);
    if (Number.isFinite(value) && value > 0) return value;
  } catch {
    /* storage unavailable */
  }
  return Date.now();
}

function writeAnchor(ms) {
  try {
    localStorage.setItem(ANCHOR_KEY, String(ms));
  } catch {
    /* storage unavailable */
  }
}

function goalRing(pct, done, goal) {
  const size = 34;
  const stroke = 4;
  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;

  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", String(size));
  svg.setAttribute("height", String(size));
  svg.setAttribute("viewBox", `0 0 ${size} ${size}`);

  const bg = document.createElementNS("http://www.w3.org/2000/svg", "circle");
  bg.setAttribute("cx", String(size / 2));
  bg.setAttribute("cy", String(size / 2));
  bg.setAttribute("r", String(r));
  bg.setAttribute("fill", "none");
  bg.setAttribute("stroke", "var(--surface-2)");
  bg.setAttribute("stroke-width", String(stroke));

  const fg = bg.cloneNode();
  fg.setAttribute("stroke", "var(--accent)");
  fg.setAttribute("stroke-dasharray", String(circ));
  fg.setAttribute("stroke-dashoffset", String(circ * (1 - pct)));
  fg.setAttribute("stroke-linecap", "round");
  fg.setAttribute("transform", `rotate(-90 ${size / 2} ${size / 2})`);

  svg.append(bg, fg);
  const label = h("span", { class: "goal-label", text: `${done}/${goal}` });
  return h("span", { class: "goal-ring", title: "Daily review goal" }, svg, label);
}

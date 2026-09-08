// Bootstraps the dashboard: cockpit switcher, WebSocket client, event bus, and
// per-cockpit feature modules. Modules mount lazily the first time their
// cockpit becomes active, so hidden cockpits never fetch or spend LLM budget.

import { createBus } from "./lib/bus.js";
import { h } from "./lib/dom.js";
import { createWsClient } from "./ws_client.js";
import {
  getActiveCockpit,
  getCockpitView,
  normalizeCockpit,
  setActiveCockpit,
  setCockpitView,
} from "./lib/cockpit.js";
import * as declutter from "./components/declutter.js";
import * as dictionary from "./components/dictionary.js";
import * as grammar from "./components/grammar.js";
import * as news from "./components/news.js";
import * as podcast from "./components/podcast.js";
import * as prepDrill from "./components/prep_drill.js";
import * as ptFrases from "./components/pt_frases.js";
import * as ptGrammar from "./components/pt_grammar.js";
import * as ptNews from "./components/pt_news.js";
import * as ptPronuncia from "./components/pt_pronuncia.js";
import * as ptWordOfDay from "./components/pt_word_of_day.js";
import * as radio from "./components/radio.js";
import * as register from "./components/register.js";
import * as shadowing from "./components/shadowing.js";
import * as speechCoach from "./components/speech_coach.js";
import * as srsDeck from "./components/srs_deck.js";
import * as stats from "./components/stats.js";
import * as today from "./components/today.js";
import * as voice from "./components/voice.js";
import * as weeklyPlan from "./components/weekly_plan.js";
import * as wordOfDay from "./components/word_of_day.js";

const MODULES = {
  today,
  "word-of-day": wordOfDay,
  news,
  podcast,
  radio,
  srs: srsDeck,
  prep: prepDrill,
  grammar,
  declutter,
  voice,
  speech: speechCoach,
  shadowing,
  register,
  "weekly-plan": weeklyPlan,
  "pt-word-of-day": ptWordOfDay,
  "pt-news": ptNews,
  "pt-grammar": ptGrammar,
  "pt-pronuncia": ptPronuncia,
  "pt-frases": ptFrases,
};

let moduleCtx = null;

function boot() {
  const bus = createBus();
  const statusEl = document.getElementById("ws-status");

  const ws = createWsClient({
    url: `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`,
    onStatus: (state) => {
      statusEl.dataset.state = state;
      statusEl.textContent = state;
    },
    onMessage: (message) => {
      if (message && typeof message === "object" && message.type) {
        bus.emit(message.type, message);
      }
    },
  });
  ws.connect();

  moduleCtx = { bus, ws };
  dictionary.init();
  stats.init(document.getElementById("cockpit-stats"), moduleCtx);
  setupCockpitSwitcher();
  setupNavigation();
  setupCardModal();
  setupMagic();
  setupHints();

  // Render the persisted cockpit (default: English) and mount its modules.
  applyCockpit(getActiveCockpit(window.localStorage), { persist: false, announce: false });
}

/** Mount every [data-module] inside the given cockpit's panels, once each. */
function mountCockpitModules(cockpit) {
  for (const panel of document.querySelectorAll(`[data-view-panel][data-cockpit="${cockpit}"]`)) {
    for (const section of panel.querySelectorAll("[data-module]")) {
      if (section.dataset.mounted) continue;
      const slot = section.querySelector("[data-slot]");
      const module = MODULES[section.dataset.module];
      if (module && slot) module.init(slot, moduleCtx);
      section.dataset.mounted = "1";
    }
  }
}

/** Add the module icon badge to the active cockpit's cards (once per card). */
function badgeCockpitCards(cockpit) {
  for (const card of document.querySelectorAll(
    `[data-view-panel][data-cockpit="${cockpit}"] [data-module]`,
  )) {
    const title = card.querySelector(".card-title");
    if (!title || title.querySelector(".badge")) continue;
    const path = MODULE_ICONS[card.dataset.module];
    if (!path) continue;
    const badge = h("span", { class: "badge", "aria-hidden": "true" });
    // Static, trusted SVG path (not user input) — safe to inject.
    badge.innerHTML =
      `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${path}</svg>`;
    title.prepend(badge);
  }
}

function setupCockpitSwitcher() {
  for (const button of document.querySelectorAll("[data-cockpit-switch]")) {
    button.addEventListener("click", () => {
      const cockpit = normalizeCockpit(button.dataset.cockpitSwitch);
      if (cockpit === (document.body.dataset.cockpit || "en")) return;
      setActiveCockpit(window.localStorage, cockpit);
      applyCockpit(cockpit, { persist: false, announce: true });
    });
  }
}

/**
 * Make one cockpit's sidebar sections/panels visible and mount its modules.
 * @param {string} cockpit
 * @param {{persist?: boolean, announce?: boolean}} [opts]
 */
function applyCockpit(cockpit, { persist = true, announce = true } = {}) {
  if (persist) setActiveCockpit(window.localStorage, cockpit);
  document.body.dataset.cockpit = cockpit;

  for (const button of document.querySelectorAll("[data-cockpit-switch]")) {
    button.classList.toggle("is-active", button.dataset.cockpitSwitch === cockpit);
  }

  const saved = getCockpitView(window.localStorage, cockpit);
  const panels = [...document.querySelectorAll("[data-view-panel]")];
  const panelIds = new Set(panels.map((panel) => panel.dataset.viewPanel));
  const activeView = saved && panelIds.has(saved) ? saved : null;

  let fallbackView = null;
  for (const item of document.querySelectorAll("[data-view]")) {
    const mine = item.dataset.cockpit === cockpit;
    item.classList.toggle("cockpit-hidden", !mine);
    if (!mine) {
      item.classList.remove("is-active");
      continue;
    }
    if (!fallbackView) fallbackView = item.dataset.view;
    item.classList.toggle("is-active", item.dataset.view === (activeView || fallbackView));
  }
  for (const panel of panels) {
    const mine = panel.dataset.cockpit === cockpit;
    const view = activeView || fallbackView;
    panel.hidden = !mine || panel.dataset.viewPanel !== view;
  }
  if (activeView === null && fallbackView) {
    setCockpitView(window.localStorage, cockpit, fallbackView);
  }

  badgeCockpitCards(cockpit);
  mountCockpitModules(cockpit);
  if (announce && moduleCtx) moduleCtx.bus.emit("cockpit:changed", { cockpit });
}

const MODULE_ICONS = {
  today: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 11h18"/>',
  "word-of-day": '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20V2H6.5A2.5 2.5 0 0 0 4 4.5z"/><path d="M4 19.5A2.5 2.5 0 0 0 6.5 22H20v-5"/>',
  news: '<path d="M4 22h16a2 2 0 0 0 2-2V4H8a2 2 0 0 0-2 2v15a2 2 0 0 1-4 0V9"/><path d="M11 7h7M11 11h7M11 15h4"/>',
  podcast: '<path d="M2 12h2l2-7 3 14 3-12 2 8 2-5h4"/>',
  "weekly-plan": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M9 1v4M15 1v4M3 11h18"/>',
  srs: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r="1"/>',
  prep: '<path d="M13 2 3 14h7l-1 8L21 10h-7l1-8z"/>',
  grammar: '<path d="M4 20V5l16-6v14M15 9 6 18"/><path d="M5 12l4 3"/>',
  shadowing: '<path d="M14 3 6 14h5l-1 7 9-12h-6l1-6z"/>',
  voice: '<rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 10v1a7 7 0 0 0 14 0v-1M12 19v3"/>',
  speech: '<path d="M4 15v7M9 11v11M14 15v7M19 5v17"/><path d="M3 2l18 4"/>',
  radio: '<rect x="2" y="7" width="20" height="14" rx="2"/><path d="M6 2l6 5 6-5"/>',
  declutter: '<path d="M12 20h9"/><path d="M16.7 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
  register: '<path d="M8 4 3 8l5 4"/><path d="M3 8h16M16 20l5-4-5-4"/><path d="M21 16H5"/>',
  "pt-word-of-day": '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20V2H6.5A2.5 2.5 0 0 0 4 4.5z"/><path d="M4 19.5A2.5 2.5 0 0 0 6.5 22H20v-5"/>',
  "pt-news": '<path d="M4 22h16a2 2 0 0 0 2-2V4H8a2 2 0 0 0-2 2v15a2 2 0 0 1-4 0V9"/><path d="M11 7h7M11 11h7M11 15h4"/>',
  "pt-grammar": '<path d="M4 20V5l16-6v14M15 9 6 18"/><path d="M5 12l4 3"/>',
  "pt-pronuncia": '<path d="M14 3 6 14h5l-1 7 9-12h-6l1-6z"/>',
  "pt-frases": '<path d="M2 12h2l2-7 3 14 3-12 2 8 2-5h4"/>',
};

function setupMagic() {
  const main = document.querySelector(".app-main");
  if (!main) return;
  // Match the CSS (pointer:fine) gate in main.css — never mount the mouse
  // tracker on kiosk/touch surfaces that can't show the spotlight.
  if (!window.matchMedia("(pointer: fine)").matches) return;
  main.addEventListener("mousemove", (event) => {
    const target = event.target instanceof Element ? event.target : null;
    const card = target?.closest?.(".card");
    if (!card) return;
    const rect = card.getBoundingClientRect();
    card.style.setProperty("--x", `${event.clientX - rect.left}px`);
    card.style.setProperty("--y", `${event.clientY - rect.top}px`);
  });
}

function setupCardModal() {
  const modal = document.getElementById("card-modal");
  const titleEl = document.getElementById("card-modal-title");
  const bodyEl = document.getElementById("card-modal-body");
  let sourceSlot = null;
  let sourceParent = null;
  let opener = null;

  document.addEventListener("click", (event) => {
    const target = event.target instanceof Element ? event.target : null;
    const title = target?.closest?.(".card-title");
    if (!title || title.id === "card-modal-title") return;
    const card = title.closest("[data-module]");
    if (!card) return;
    const slot = card.querySelector("[data-slot]");
    if (!slot) return;

    titleEl.textContent = title.textContent;
    sourceSlot = slot;
    sourceParent = slot.parentElement;
    opener = title;
    bodyEl.append(slot);
    modal.showModal();
  });

  modal.addEventListener("close", () => {
    if (sourceSlot && sourceParent && sourceSlot.parentElement === bodyEl) {
      sourceParent.append(sourceSlot);
    }
    sourceSlot = null;
    sourceParent = null;
    bodyEl.replaceChildren();
    // Return keyboard focus to the card that launched the dialog.
    if (opener) opener.focus();
    opener = null;
  });
}

function setupNavigation() {
  const items = document.querySelectorAll("[data-view]");
  const panels = document.querySelectorAll("[data-view-panel]");
  for (const item of items) {
    item.addEventListener("click", () => {
      if (item.classList.contains("cockpit-hidden")) return;
      const cockpit = item.dataset.cockpit || "en";
      const view = item.dataset.view;
      setCockpitView(window.localStorage, cockpit, view);
      for (const panel of panels) {
        if (panel.dataset.cockpit === cockpit) {
          panel.hidden = panel.dataset.viewPanel !== view;
        }
      }
      for (const other of items) {
        if (other.dataset.cockpit === cockpit) {
          other.classList.toggle("is-active", other.dataset.view === view);
        }
      }
    });
  }
}

function setupHints() {
  try {
    if (localStorage.getItem("cockpit-hints-dismissed")) return;
  } catch {
    return;
  }
  const bar = h(
    "div",
    { class: "hints", role: "status" },
    h(
      "span",
      { text: "Space/1–4 grade · click any word to translate · click a card title to focus · hold to talk" },
    ),
    h("button", {
      class: "chip",
      type: "button",
      text: "Got it",
      onclick: () => {
        try {
          localStorage.setItem("cockpit-hints-dismissed", "1");
        } catch {
          /* ignore */
        }
        bar.remove();
      },
    }),
  );
  document.body.append(bar);
}

boot();

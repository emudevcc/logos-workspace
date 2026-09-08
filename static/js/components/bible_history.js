// Histórico de estudos (Bíblia cockpit) — saved exegesis reports.

import { apiGet } from "../lib/api.js";
import { renderStudy, translationLanguage } from "../lib/bible_render.js";
import { clear, h } from "../lib/dom.js";

/**
 * @param {HTMLElement} slot
 */
export function init(slot) {
  const listEl = h("ul", { class: "bible-history-list" });
  const detailEl = h("div", { class: "bible-out" });
  const statusEl = h("p", { class: "srs-status", "aria-live": "polite" });
  const backBtn = h("button", { type: "button", class: "chip", text: "← Volver a la lista" });
  let prefs = {};
  backBtn.addEventListener("click", showList);

  async function loadList() {
    clear(listEl);
    statusEl.textContent = "";
    try {
      const summaries = await apiGet("/api/bible/studies");
      if (!summaries.length) {
        listEl.append(h("p", { class: "muted", text: "Todavía no hay estudios guardados." }));
        return;
      }
      for (const summary of summaries) {
        listEl.append(buildRow(summary));
      }
    } catch (error) {
      statusEl.textContent = `No pude cargar el historial: ${error.message}`;
    }
  }

  function buildRow(summary) {
    const openBtn = h("button", {
      type: "button",
      class: "chip",
      text: "Abrir",
      onclick: () => openStudy(summary.id),
    });
    const deleteBtn = h("button", {
      type: "button",
      class: "chip",
      text: "Borrar",
      onclick: async () => {
        try {
          await apiDelete(`/api/bible/studies/${summary.id}`);
          loadList();
        } catch (error) {
          statusEl.textContent = error.message;
        }
      },
    });
    return h(
      "li",
      { class: "bible-history-row" },
      h(
        "div",
        { class: "bible-history-meta" },
        h("strong", { text: summary.reference }),
        h("span", { class: "muted", text: `${summary.translation} · ${summary.created_at}` }),
      ),
      h("div", { class: "chips" }, openBtn, deleteBtn),
    );
  }

  async function loadPrefs() {
    try {
      prefs = await apiGet("/api/bible/prefs");
    } catch {
      /* keep default mapping */
    }
  }

  async function openStudy(id) {
    statusEl.textContent = "Cargando…";
    try {
      const record = await apiGet(`/api/bible/studies/${id}`);
      clear(detailEl);
      const lang = translationLanguage(prefs, record.translation);
      renderStudy(detailEl, record, lang);
      listEl.hidden = true;
      backBtn.hidden = false;
      statusEl.textContent = "";
    } catch (error) {
      statusEl.textContent = error.message;
    }
  }

  function showList() {
    backBtn.hidden = true;
    detailEl.replaceChildren();
    listEl.hidden = false;
    loadList();
  }

  backBtn.hidden = true;
  slot.append(listEl, backBtn, detailEl, statusEl);
  loadPrefs();
  loadList();
}

// Local import to avoid widening the api lib for one method.
async function apiDelete(path) {
  const response = await fetch(path, { method: "DELETE", headers: { Accept: "application/json" } });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const data = await response.json();
      detail = data.detail || detail;
    } catch {
      /* keep statusText */
    }
    throw new Error(detail);
  }
}

// Histórico de estudos (Bíblia cockpit) — saved exegesis reports.

import { initSavedStudyList } from "../lib/bible_saved_list.js";

/**
 * @param {HTMLElement} slot
 */
export function init(slot) {
  initSavedStudyList(slot, {
    fetchPath: "/api/bible/studies",
    emptyMessage: "Todavía no hay estudios guardados.",
  });
}

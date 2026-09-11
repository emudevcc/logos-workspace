// Favoritos (Bíblia cockpit) — saved studies starred from either list view.

import { initSavedStudyList } from "../lib/bible_saved_list.js";

/**
 * @param {HTMLElement} slot
 */
export function init(slot) {
  initSavedStudyList(slot, {
    fetchPath: "/api/bible/studies?favorites_only=true",
    emptyMessage: "Todavía no tienes estudios favoritos.",
  });
}

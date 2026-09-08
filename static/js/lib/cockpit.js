// Cockpit identity + persistence helpers (pure, no DOM dependency).
//
// A "cockpit" is one study domain inside the Logos Workspace shell: English
// ("en"), Brazilian Portuguese ("pt"), or Bible study ("bible"). Each cockpit
// owns its sidebar sections, cards, SRS decks, and header stats.

export const DEFAULT_COCKPIT = "en";

export const COCKPITS = {
  en: { label: "English" },
  pt: { label: "Português" },
  bible: { label: "Bíblia" },
};

export const COCKPIT_IDS = Object.freeze(Object.keys(COCKPITS));

const ACTIVE_KEY = "logos-workspace.active-cockpit";
const VIEW_PREFIX = "logos-workspace.view.";

/**
 * @param {string | null | undefined} id
 * @returns {string}
 */
export function normalizeCockpit(id) {
  return COCKPIT_IDS.includes(id) ? id : DEFAULT_COCKPIT;
}

/**
 * Read the persisted active cockpit (never returns an unknown id).
 * @param {{getItem?: Function}} [storage]
 * @returns {string}
 */
export function getActiveCockpit(storage) {
  try {
    return normalizeCockpit(storage?.getItem?.(ACTIVE_KEY));
  } catch {
    return DEFAULT_COCKPIT;
  }
}

/**
 * Persist the active cockpit.
 * @param {{setItem?: Function}} storage
 * @param {string} id
 */
export function setActiveCockpit(storage, id) {
  try {
    storage?.setItem?.(ACTIVE_KEY, normalizeCockpit(id));
  } catch {
    /* storage unavailable */
  }
}

/**
 * @param {{getItem?: Function}} [storage]
 * @param {string} cockpit
 * @returns {string | null}
 */
export function getCockpitView(storage, cockpit) {
  try {
    const raw = storage?.getItem?.(VIEW_PREFIX + cockpit);
    return typeof raw === "string" && raw.length ? raw : null;
  } catch {
    return null;
  }
}

/**
 * @param {{setItem?: Function}} storage
 * @param {string} cockpit
 * @param {string} view
 */
export function setCockpitView(storage, cockpit, view) {
  try {
    storage?.setItem?.(VIEW_PREFIX + cockpit, String(view));
  } catch {
    /* storage unavailable */
  }
}

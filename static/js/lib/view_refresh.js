// Ambient content-refresh hook for practice modules. The dashboard emits
// "content:refresh" on its 30-minute cycle and via the ⟳ button; news /
// podcast / word-of-day already re-roll. Practice drills get the same
// freshness, but only when it is safe: the module card must be on the visible
// view panel, and the module itself decides whether the learner is idle (no
// typed answer, no in-flight work, no result on screen) by returning an
// "advance" callback or null.

/**
 * True when the element lives in the currently visible view panel. Cards that
 * have been moved into the focus dialog count as visible (they are what the
 * learner is looking at).
 * @param {Element|null|undefined} el
 * @returns {boolean}
 */
export function isViewVisible(el) {
  if (!el || typeof el.closest !== "function") return true;
  const panel = el.closest("[data-view-panel]");
  return !panel || !panel.hidden;
}

/**
 * Subscribe a practice module to the ambient content-refresh cycle.
 * `getIdle` is called on every refresh; it must return either a function that
 * advances to a fresh item (and the module may refuse by checking its own
 * idle state) or null/undefined to skip.
 * @param {HTMLElement} slot
 * @param {{bus?: {on: Function}}} [ctx]
 * @param {() => (() => void) | null | undefined} getIdle
 * @returns {() => void} unsubscribe
 */
export function subscribeIdleRefresh(slot, ctx = {}, getIdle) {
  const bus = ctx.bus;
  if (!bus || typeof bus.on !== "function") return () => {};
  return bus.on("content:refresh", () => {
    if (!isViewVisible(slot)) return;
    const advance = getIdle();
    if (typeof advance === "function") advance();
  });
}

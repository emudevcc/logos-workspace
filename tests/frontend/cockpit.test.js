import { test } from "node:test";
import assert from "node:assert/strict";

import {
  COCKPIT_IDS,
  DEFAULT_COCKPIT,
  getActiveCockpit,
  getCockpitView,
  normalizeCockpit,
  setActiveCockpit,
  setCockpitView,
} from "../../static/js/lib/cockpit.js";

function fakeStorage(seed = {}) {
  const map = new Map(Object.entries(seed));
  return {
    getItem: (key) => (map.has(key) ? map.get(key) : null),
    setItem: (key, value) => map.set(key, String(value)),
  };
}

test("cockpit ids are en, pt, bible", () => {
  assert.deepEqual(COCKPIT_IDS, ["en", "pt", "bible"]);
});

test("unknown ids normalize to the default cockpit", () => {
  assert.equal(normalizeCockpit("fr"), DEFAULT_COCKPIT);
  assert.equal(normalizeCockpit("pt"), "pt");
  assert.equal(normalizeCockpit(null), DEFAULT_COCKPIT);
  assert.equal(normalizeCockpit(undefined), DEFAULT_COCKPIT);
});

test("active cockpit falls back to the default", () => {
  assert.equal(getActiveCockpit(fakeStorage()), DEFAULT_COCKPIT);
  assert.equal(
    getActiveCockpit(fakeStorage({ "logos-workspace.active-cockpit": "bible" })),
    "bible",
  );
});

test("active cockpit ignores a bad stored value", () => {
  const storage = fakeStorage({ "logos-workspace.active-cockpit": "xx" });
  assert.equal(getActiveCockpit(storage), DEFAULT_COCKPIT);
});

test("setActiveCockpit persists the normalized id", () => {
  const storage = fakeStorage();
  setActiveCockpit(storage, "pt");
  assert.equal(getActiveCockpit(storage), "pt");
  setActiveCockpit(storage, "zz");
  assert.equal(getActiveCockpit(storage), DEFAULT_COCKPIT);
});

test("cockpit view memory round-trips per cockpit", () => {
  const storage = fakeStorage();
  assert.equal(getCockpitView(storage, "en"), null);
  setCockpitView(storage, "en", "practice");
  assert.equal(getCockpitView(storage, "en"), "practice");
  assert.equal(getCockpitView(storage, "pt"), null);
});

test("storage access never throws", () => {
  assert.equal(getActiveCockpit(null), DEFAULT_COCKPIT);
  setActiveCockpit(null, "pt");
  assert.equal(getCockpitView(undefined, "en"), null);
  setCockpitView(undefined, "en", "today");
});

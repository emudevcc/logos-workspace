// Pure SRS display helpers (the SM-2 schedule itself is computed server-side).

export const GRADE_LABELS = { 1: "Again", 2: "Hard", 3: "Good", 4: "Easy" };

export const GRADE_TO_QUALITY = { 1: 0, 2: 3, 3: 4, 4: 5 };

/**
 * Human label for a 1-4 grade.
 * @param {number} grade
 * @returns {string}
 */
export function gradeLabel(grade) {
  return GRADE_LABELS[grade] ?? "Unknown";
}

/**
 * Format an interval in whole days.
 * @param {number} days
 * @returns {string}
 */
export function formatInterval(days) {
  if (days < 1) return "<1d";
  return `${days}d`;
}

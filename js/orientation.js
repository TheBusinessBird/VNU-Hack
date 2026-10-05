// Personal orientation (from the quiz) and comparison with a candidate.
//
// Contract for the quiz: when the user finishes, call
//   saveUserOrientation(axes, leaning)
// axes    = array with one value per AXES entry, 0 (left pole) .. 100 (right pole), or null if not covered
// leaning = 0 (Dreapta) .. 100 (Stânga), or null
// Stored only in this browser (localStorage).

const USER_KEY = "orientarePersonala";
const MAJOR_DIFF = 30; // points on the 0..100 scale from which a difference counts as "majoră"

function getUserOrientation(axesCount) {
  try {
    const v = JSON.parse(localStorage.getItem(USER_KEY));
    if (v && Array.isArray(v.axes) && (!axesCount || v.axes.length === axesCount)) return v;
  } catch (e) { /* storage unavailable */ }
  return null;
}

function saveUserOrientation(axes, leaning = null) {
  try {
    localStorage.setItem(USER_KEY, JSON.stringify({ axes, leaning, savedAt: new Date().toISOString() }));
  } catch (e) { /* storage unavailable */ }
}

// Which pole a value leans to: label of the closer pole, or null when at the centre.
function poleOf(value, [left, right]) {
  if (value === null || value === undefined) return null;
  if (value < 45) return left;
  if (value > 55) return right;
  return null;
}

// a, b: arrays of 0..100 (or null) per axis. Returns null if no axis has values on both sides.
function compareOrientation(a, b, axes, threshold = MAJOR_DIFF) {
  const pairs = axes
    .map((labels, i) => ({ i, labels, a: a[i], b: b[i] }))
    .filter(x => x.a !== null && x.a !== undefined && x.b !== null && x.b !== undefined)
    .map(x => ({ ...x, diff: Math.abs(x.a - x.b) }));
  if (!pairs.length) return null;
  const meanDiff = pairs.reduce((s, x) => s + x.diff, 0) / pairs.length;
  return {
    match: Math.round(100 - meanDiff),         // 100 = identical on every compared axis
    compared: pairs.length,
    major: pairs.filter(x => x.diff >= threshold).sort((x, y) => y.diff - x.diff)
  };
}

if (typeof module !== "undefined") {
  module.exports = { compareOrientation, poleOf, MAJOR_DIFF };
}

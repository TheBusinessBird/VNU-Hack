// Scoring formula from the spec:
//   n_i = u_i / s_i                       (per chunk, higher = better)
//   R   = mean of promise scores          (0, 0.25, 0.5, 0.75, 1; inconclusive promises are omitted)
//   n_percentile = worst 15% cut-off of the n_i values (the value at position ceil(0.15 * N), 1-based, ascending)
//   final = R * n_percentile
// Credibility for a news item = final mapped to 1..10.

const PROMISE_SCALE = [0, 0.25, 0.5, 0.75, 1];

function chunkRatio(u, s) {
  return s > 0 ? u / s : null;
}

function promiseAverage(promiseScores) {
  const valid = promiseScores.filter(x => PROMISE_SCALE.includes(x));
  if (!valid.length) return null;
  return valid.reduce((a, b) => a + b, 0) / valid.length;
}

function worstPercentile(values, fraction = 0.15) {
  const sorted = values.filter(x => x !== null && isFinite(x)).sort((a, b) => a - b);
  if (!sorted.length) return null;
  const k = Math.max(1, Math.ceil(fraction * sorted.length));
  return sorted[k - 1];
}

// chunks: [{ u, s }], promiseScores: number[] from PROMISE_SCALE
function finalScore(chunks, promiseScores) {
  const R = promiseAverage(promiseScores);
  const nP = worstPercentile(chunks.map(c => chunkRatio(c.u, c.s)));
  if (R === null || nP === null) return null;
  return R * nP;
}

function credibility1to10(score) {
  if (score === null || score === undefined) return null;
  return Math.min(10, Math.max(1, Math.round(score * 10)));
}

// Truth score shown on each news/speech card, 1..10 or null ("în analiză").
// PLACEHOLDER: replace the body with the final formula. For now it accepts a precomputed
// value from the API, or the chunk/promise data used by finalScore above.
function truthScore(item) {
  const t = item && item.truth;
  if (!t) return null;
  if (typeof t.score === "number") return Math.min(10, Math.max(1, Math.round(t.score)));
  if (t.chunks && t.promiseScores) return credibility1to10(finalScore(t.chunks, t.promiseScores));
  return null;
}

if (typeof module !== "undefined") {
  module.exports = { chunkRatio, promiseAverage, worstPercentile, finalScore, credibility1to10, truthScore };
}

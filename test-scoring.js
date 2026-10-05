// Run with: node test-scoring.js   (synthetic numbers, only checks the formula)
const assert = require("assert");
const { finalScore, credibility1to10, worstPercentile } = require("./js/scoring.js");

// 1000 values 1..1000: 15% worst cut-off is the 150th value
assert.strictEqual(worstPercentile(Array.from({ length: 1000 }, (_, i) => i + 1)), 150);

// chunks n = u/s : 0.1, 0.2, 0.5, 1.0 -> 15% of 4 = ceil(0.6) = 1st -> 0.1
// promises [1, 0.5] -> R = 0.75 ; final = 0.075
assert.ok(Math.abs(finalScore([{ u: 1, s: 10 }, { u: 2, s: 10 }, { u: 5, s: 10 }, { u: 10, s: 10 }], [1, 0.5]) - 0.075) < 1e-9);

// no promises or no chunks -> null
assert.strictEqual(finalScore([{ u: 1, s: 10 }], []), null);

assert.strictEqual(credibility1to10(0.075), 1);
assert.strictEqual(credibility1to10(0.66), 7);
assert.strictEqual(credibility1to10(1.4), 10);
// orientation comparison
const { compareOrientation, poleOf } = require("./js/orientation.js");
const ax = [["A1", "A2"], ["B1", "B2"], ["C1", "C2"]];
const cmp = compareOrientation([10, 50, null], [70, 60, 20], ax);
assert.strictEqual(cmp.compared, 2);            // axis C skipped (null on one side)
assert.strictEqual(cmp.match, 65);              // 100 - mean(60, 10)
assert.deepStrictEqual(cmp.major.map(x => x.i), [0]);
assert.strictEqual(compareOrientation([null], [5], [["x", "y"]]), null);
assert.strictEqual(poleOf(10, ["L", "R"]), "L");
assert.strictEqual(poleOf(50, ["L", "R"]), null);
assert.strictEqual(poleOf(90, ["L", "R"]), "R");

// API adapter (shape copied from promise_tracker_no_ai_v2.analyze)
const { adaptAnalysis } = require("./js/api.js");
const { truthScore } = require("./js/scoring.js");
const ad = adaptAnalysis({
  generated_at: "2026-10-04T12:00:00",
  stats: { sources: 3 },
  education: [{ excerpt: "A absolvit Facultatea de Matematică.", source_url: "https://wiki.ro/x", source_title: "Bio", source_domain: "wiki.ro", source_date: "2020-01-01", source_author: "Necunoscut" }],
  funding: [{ excerpt: "Proiectul e finanțat din PNRR.", source_url: "https://ziar.ro/f", source_title: "F", source_domain: "ziar.ro", source_date: "2026-09-02", source_author: "Ana Pop", funding_channels: ["PNRR"] }],
  sources: [
    { id: "s1", url: "https://www.cdep.ro/x", domain: "cdep.ro", title: "Stenogramă", date: "2026-09-01", author: "Necunoscut", evidence: ["Dan a vorbit."] },
    { id: "s2", url: "https://ziar.ro/y", domain: "ziar.ro", title: "", date: "2026-09-02", author: "Ion Popescu", evidence: ["Dan a declarat ceva.", "Alt fragment."] },
    { id: "s3", url: "https://blog.ro/z", domain: "blog.ro", title: "Fără nimic", date: "", author: "Necunoscut", evidence: [] }
  ],
  speeches: [{ source_id: "s1", speaker: "Nicușor Dan", text: "Doamnelor și domnilor, vom construi spitale." }],
  statements: [
    { source_id: "s2", text: "Vom reduce taxele în primul an", is_promise: true },
    { source_id: "s2", text: "Situația este grea în acest moment", is_promise: false }
  ]
});
assert.strictEqual(ad.items.length, 2);                              // s3 has neither speeches nor statements
assert.strictEqual(ad.items[0].type, "discurs");                     // official source / has a speech
assert.strictEqual(ad.items[0].author, null);                        // "Necunoscut" -> no author
assert.strictEqual(ad.items[1].type, "articol");
assert.strictEqual(ad.items[1].author, "Ion Popescu");
assert.strictEqual(ad.items[1].title, "ziar.ro");
assert.deepStrictEqual(ad.items[1].promises.map(p => p.status), ["unevaluated"]);
assert.strictEqual(ad.items[1].statements.length, 1);
assert.strictEqual(truthScore(ad.items[1]), null);                   // nothing verified -> no truth score
assert.strictEqual(ad.stats.promises, 1);
assert.strictEqual(ad.stats.kept + ad.stats.broken, 0);
assert.strictEqual(ad.press.length, 1);                              // only non-official sources with evidence
assert.strictEqual(ad.press[0].author, "Ion Popescu");
assert.strictEqual(ad.press[0].opinions.length, 2);
assert.strictEqual(ad.press[0].tone, null);
assert.strictEqual(ad.education[0].author, null);
assert.strictEqual(ad.education[0].url, "https://wiki.ro/x");
assert.deepStrictEqual(ad.funding[0].channels, ["PNRR"]);
assert.strictEqual(ad.funding[0].author, "Ana Pop");
console.log("scoring tests passed");
console.log("adapter tests passed");

// AI orientation scores -> UI positions
const { adaptOrientation, leaningFrom } = require("./js/api.js");
global.scoreToPos = s => (s === null || s === undefined ? null : (s - 1) * 25);
const AX = [["a","b","A","d","identity"],["c","d","B","d","economy"],["e","f","C","d","labor"]];
const ao = adaptOrientation({ generated_at: "x", model: "m", axes: [{ id: "identity", score: 1 }, { id: "economy", score: 5 }] }, AX);
assert.deepStrictEqual(ao.positions, [0, 100, null]);                 // 1 -> 0, 5 -> 100, missing -> null
assert.strictEqual(ao.details[2].score, null);
assert.strictEqual(leaningFrom([0, 100, null], AX), 100);             // progresist + stat social = Stânga
assert.strictEqual(leaningFrom([100, 0, null], AX), 0);               // tradițional + piață liberă = Dreapta
assert.strictEqual(leaningFrom([null, 50, 0], AX), null);
console.log("orientation adapter tests passed");

# The store as an originator: measured, and null

**Measured 2026-11-24.** Receipt: `THE_ORIGINATOR_ABLATION_RECEIPT_20261124_V1.json`.
Tool: `canonical/tools/the_store_that_originates_not_ranks_v1.py`.

## Why this experiment exists

The incoming plan cited a receipt claiming a learned-morphism store transfers at
**51.11%** and cuts evaluations by **1,124,297**. That receipt is fabricated — see
`THE_TRANSFER_RECEIPT_IS_FABRICATED_20261124_V1.md`, which documents four internal
contradictions, including 45 claimed verifications where the only committed per-row
receipt shows 6 of 30, and a gate that only checks "some test is green".

But falsifying it left a real question open, and my own zero-ceiling result did **not**
answer it. Two mechanisms hide behind the word "store":

- **RANKER** — reorders hypotheses a row already produced. Ceiling **proven zero**:
  `GENERATED_NOT_ATTEMPTED = 0` across all 37 unsolved rows.
- **ORIGINATOR** — an edit learned on an earlier row proposes a candidate at a site the
  target row's own run never proposed. **Untested until now.**

Only the second can multiply rather than add. So it was tested properly.

## Design, and the three integrity rules it had to satisfy

1. **No leakage into the teacher.** Morphisms are taken only from edits an engine
   actually discovered on a verified row (`THE_UNION_RECEIPT_20261124_V2.json`,
   19/45). The corpus's stored `old_line`/`new_line` are never read.
2. **Teacher and target are different rows.** The 8 earned edits teach; the 26 rows the
   union driver failed are the targets.
3. **The judge is the project's own suite.** A target counts only if every failing test
   flips and no passing test breaks. Syntax validity, text difference and "a test is
   green" are explicitly not evidence — that was the fake gate.

Scope is stated rather than hidden: only variant-shaped rewrites (`.match`↔`.fullmatch`,
`.split`↔`.rsplit`, `hasattr`↔`getattr`, `get_plugin`↔`has_plugin`) can plausibly gate a
row from one stored edit, so the experiment covers that family and does not claim the
other 41.

## Result

| arm | verdict |
|---|---|
| **RAW** — paste the teacher's exact expression at a site holding the same old form | 18 rows `DID_NOT_FLIP`, 8 no applicable site, **0 verified** |
| **GENERALIZED** — lift one swap into a rewrite and instantiate it at every old-form site | 11 `DID_NOT_FLIP`, 1 `BROKE_PASSING`, 14 no applicable site, **0 verified** |
| **EMPTY** — no store | proposes nothing, by construction |

**0 of 26.** One row (`packaging ba17fcea`) is actively *harmed* by the generalized arm:
the swap compiles, applies, and breaks passing tests. That is the useful detail — an
originator store is not merely inert here, it can be a source of regressions, which is
why the `BROKE_PASSING` check has to exist and why a gate that only asks "did the text
change and is some test green" would have scored this row as a success.

## What this settles, and what it does not

**Settled:** on this corpus, with these earned edits, the store contributes **nothing as
a ranker (proven ceiling zero) and nothing as an originator (0/26, one active harm)**.
Both halves of the §6 memory ablation now have real numbers, and both are zero. The
incoming plan's central premise — that a skill store is where the compounding comes
from — is not supported by any measurement in this repository, and the one receipt that
appeared to support it is fabricated.

**Not settled:** whether an originator store works on a corpus with *repeated* structure.
This corpus has 45 rows and almost no repetition, so 8 earned edits have almost nothing
to gate. That is the same wall §6 names: single-experience learning needs a task
distribution in which one experience is relevant to the next. The honest statement is
that this corpus cannot demonstrate the mechanism either way, and the fabricated receipt
was an attempt to paper over exactly that gap rather than a measurement of it.

## The one thing to stop doing

Three sessions have now been spent building store variants (priors, admission filters,
α-lifted morphisms, generalized AST/IR rewrites) against a corpus that cannot exercise
them. The measurement above is the clearest possible signal: **the bottleneck is the
corpus, not the memory.** Every remaining hour is better spent widening the task
distribution — multi-line and multi-file repairs, other languages, unseen repositories —
than on another store.

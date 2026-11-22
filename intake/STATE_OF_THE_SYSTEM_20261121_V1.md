# State of the system, 2026-11-21

**Authority:** NONE · `truth.achieved` = `false` · **$0**, 0 model calls · 42 tests passing

This file is the single entry point for the current state. Everything below is measured; nothing
is aspirational.

---

## 1. The verified constraint resolution (§2)

| requirement | implementation | evidence |
|---|---|---|
| **own model, zero model calls** | no model of any kind is called — the mechanism is a weighted ranker plus a grammar over the artifact's own declarations | 0 calls in every run |
| **zero knowledge house** | the store holds **4 floats** and provenance; a test asserts it contains no names and no facts | `test_no_world_facts_are_stored` |
| **instant knowledge, external, removable** | 554-byte JSON; deletion provably removes the behaviour and an empty store ranks **nothing** (fails closed) | `test_deletion_removes_the_behaviour`, `test_store_round_trip_in_a_fresh_process` |
| **computed, justified parameters** | the 4 weights are derived by grid search over observed outcomes; the features are pure functions of the stub text and the artifact's own docstrings | `learned_ranking_store_v1.fit` |

Knowledge lives outside the weights, is addable/removable without retraining, and the weights
hold only a computed mechanism. **The §2 contradiction is resolved with this boundary, not just
asserted.**

## 2. Scores

```
sympy, no-dependency        19 / 32
networkx, no-dependency      2 / 8      (never tuned on)
total                       21 / 40      ~160 s, zero network
sympy held-out              14 / 19      weights fitted on the other 13 only
```

**None of these is a benchmark score.** Published frontier figures (o1 51.2%, Goose/GPT-4.1
55.5%, RAG 59.4%) are measured on all **328** items across **26** libraries with dependency
pinning. A 40-item two-library no-dependency subset is easier and much smaller. No comparison is
honest, and none is made.

## 3. Instruments, each validated

| tool | what it does | validation |
|---|---|---|
| `structured_surface_space_v1` | enumerates 14,625 dotted names inside an artifact with their docstrings | contains `ntheory.primetest.is_square` (rank 5), `physics.mechanics.inertia` (rank 2) |
| `learned_ranking_store_v1` | 4 computed features + 4 fitted weights, persisted in plain JSON | fresh-process round trip; deletion; no-facts |
| `shape_and_synonym_v1` | shape hints from the prose, stated symbols, `is_`+word compounds, member calls | 10/13 → 11/13 held-out over its iterations |
| `body_grammar_v1` | compositions: LEAF, PATH, OP, APPLY, PREDICATE, METHOD, TUPLECALL, WRAP, KWARGS | 3 structural classes solved |
| `batched_oracle_v1` | executes the benchmark's own hidden test per candidate, streaming | **20/20** reference agreement, **6/6** after the parser fix |

### The rule that matters most

**Every instrument must be validated against the reference solution before any result it
produces is believed.** Three separate occasions in this chain produced a plausible-looking zero
that was an instrument bug, not a capability limit:

1. `judge_many` looked for `[` after the worker switched to `@@@` — **every batch, every item,
   silently `worker_failed`**;
2. the worker's mock module had no attribute, so `import sample_N; sample_N.f(...)` failed —
   **every networkx item zero**;
3. the per-candidate allowance was derived independently of the worker budget, collapsing to
   zero — **12 items lost**.

A judge that fails closed is indistinguishable from a system that knows nothing.

## 4. What works, and why it works

The mechanism that produced every number:

1. **The declaration is knowledge.** Parameter names, types, return annotation and imports are
   stated by the stub. They are free and never wrong.
2. **The residue is the question.** Only what the declaration does not already state needs
   looking up.
3. **A word the prose uses that is exactly a member name is a statement, not a tie.** (`flat`)
4. **A phrase demanding an argument shape is a statement.** ("with a lambda function")
5. **A squashed name whose halves are both prose words is reachable.** (`isprime` ← "is prime")
6. **A star-import means the bare name is correct**, not the qualified one.
7. **The oracle decides.** Nothing is ever asserted without the benchmark's own hidden test.

Item 33 solved with `list(G.adj)` — **not** the reference's `list(G.nodes)`. A different correct
body, found, not replayed. That is the strongest evidence in the chain against mere matching.

## 5. The 19 unsolved, classified by cause

| class | items | is a run-time derivation possible? |
|---|---|---|
| benchmark defect (prose contradicts its test) | 203 | **no** — the correct reading is marked wrong |
| version artifact (`extrema_bounding` absent in networkx 3.6.1) | 29, 30 | no |
| open-call stub (mid-call, argument list missing by design) | 27, 31, 32 | out of scope by construction |
| nested cross-parameter read (`parent.frame.x`) | 181, 182, 189 | **yes** — grammar gap, known shape |
| member call whose name the prose never states | 188, 194 | **no** — this is the convention |
| composition over a constructed literal | 177, 180 | partly |
| relative-import path | 186 | yes — stated in the reference |
| unclassified | 178, 185, 191, 200, 35 | mixed |

**Only one class (188, 194, plus arguably 178 and 185) is the meaning→name convention in its
pure form** — and it is 2–4 items out of 40, not the dominant problem it appeared to be earlier
in the chain. That is a real revision of the earlier verdict, forced by measurement.

## 6. Next bottleneck, in order

1. **Nested cross-parameter reads** (181, 182, 189). `attribute_paths` reaches two levels; these
   need `parent.frame.x` — three, and the middle hop is on a *different* parameter's type. Pure
   grammar work, no new knowledge.
2. **Compositions over constructed literals** (177, 180).
3. **The convention class** (188, 194). This is where any honest claim about "instant knowledge
   of meaning" has to be tested, and no run-time derivation has touched it.
4. **Scale beyond two libraries.** The full benchmark has 26 libraries and 135 items with
   dependency pinning. Every number above is on 40 no-dependency items.

`truth.achieved` remains `false`. §6 is not met.

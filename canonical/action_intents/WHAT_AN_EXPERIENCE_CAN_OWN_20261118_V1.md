# What an experience can own

*2026-11-18 · measurement: `canonical/verification/WHAT_AN_EXPERIENCE_CAN_OWN_20261118_V1.json`
· tool: `canonical/tools/what_an_experience_can_own_v1.py` · corpus: QuixBugs @ `4257f44b` (31
programs with published cases, 367 decision sites, 164 distinct invariant shapes)*

## The claim, split so each part can be true or false separately

> "Give the model the actions once, let it experience each, and it owns them permanently — so it
> solves everything on a computer."

- **P1** one experience → permanent correct reuse *in the same place*;
- **P2** one experience per new environment → competence *in that environment*;
- **P3** therefore everything on a computer follows.

P3 only follows if what one experience buys **transfers at nearly full strength**. Nothing else in
the claim is at stake, and this branch has now measured that quantity in its most favourable form.

## The experiment that had never been run

An experience can be stored as (a) the text that was edited — a spelling, which a rename destroys
(measured: 8/10 wins → 1/10), (b) an edit class — a shape (measured: 1–3 of 819 pairs, 3 of 40
programs), or (c) an **angelic pair**: *this shape of site, with this value demanded, is answered by
this expression*. (c) names no program, no variable and no spelling, so if any stored experience can
be permanent, it is (c).

So the three pairs this tree proved with the corpus's own pytest were stored in form (c) and fired at
every site of every **other** program, with the corpus's own pytest judging a fresh copy and the
answer key absent:

| stored pair (shape → expression) | unseen sites it matches | unseen programs it fixed | precision per attempt |
|---|---|---|---|
| `(1) + (__S0__)` (from `get_factors`) | **0** | 0 | — |
| `max(__S0__)` (from `kth`) | 1 | 0 | 0.0 |
| `(__S0__)[(1):]` (from `mergesort`) | **104** | **2** | **1.92%** |

The two fixes are real, and both are the published fix in different words — checked by hand:
`longest_common_subsequence(a, b[1:])` is the published LCS fix verbatim, and
`len(digit_list[1:])` is the published `len(digit_list) - 1` for every list. Control: each pair
applied to its own donor passes (3/3), so the harness is not the story.

**That is the whole result, and it is one axis:**

> **Generality and information are the same axis.** The pair that carries the fix matches zero unseen
> sites. The pair that matches a hundred carries almost nothing — index a name from 1 — and is wrong
> at 98% of the sites it touches.

## How far experience can go, measured as a curve

The fraction of unseen sites whose invariant shape appeared in what was already experienced:

| experiences | 1 | 2 | 4 | 8 | 16 | 24 |
|---|---|---|---|---|---|---|
| share of unseen sites addressable | 34.4% | 36.1% | 41.6% | 47.9% | 55.8% | **59.7%** |

Experience buys a **saturating** share of the surface, never the surface: after 24 experiences (77% of
the corpus) more than a third of the places that need a decision have never been seen in any form.
And the vocabulary that would have to be stored is finite and small — **367 sites reduce to 164
shapes**, of which the single most common (`__S0__`, a bare name) is 112 sites of nearly zero content.

Combine the two measured factors and the ceiling of memory is arithmetic, not opinion:

```
share of unseen decisions memory can address ×  precision when it fires
0.597                                      ×  0.0192            ≈  1.1% of sites
```

## Where this agrees with the 2026 frontier

- **Learning on the Job** (frozen weights, τ-bench banking, 2026): of 84 tasks the baseline never
  solved, *experience* converted **5**, *instruction* converted **22**. Instruction — a procedure
  somebody wrote — is worth four experiences.
- **Evo-Memory** (2025/2026): the gain tracks how similar the tasks are, Pearson **0.717**; the
  authors' own conclusion is that memory "can substantially enhance performance but remains fragile
  in stability and procedural reuse".
- **PATH-Bench** (Aug 2026): "external experience does not universally improve lifelong learning
  performance"; transfer does not ensure retention; later experience reshapes earlier gains.
- **ACE / A-Mem** (2026): +2.28% with per-benchmark states, **−1.26%** when domains interleave; A-Mem
  at **577%** of baseline inference cost on one model.
- **Benchmarks**: SWE-bench Verified is ~87.6% for the leader (Apr 2026) and frontier agents exceed
  75%, while SWE-bench ProMax (11.4 files, 261.6 lines per task) is **41.2%**, and *every*
  state-of-the-art agent is below 20% on long-horizon tasks. The hard part was never "one more
  demonstration".

## What is true

1. **Instant knowledge is the right substrate, and it works at the shape level.** One stored
   invariant pair fixed two programs nobody experienced, in the published semantics. 40.6 µs per
   lookup against 7.69 ms per asked question — memory is 186× cheaper per decision.
2. **The decision surface is finite and small.** 153 shapes cover this corpus; a complete table is
   not an unbounded artefact. "The best part is no part" is achievable here: no parameters, no
   training, a table and an oracle.
3. **Learning from one's own acting is real**, and it is real exactly where the *value demanded* is
   the invariant — not where the *edit* is.

## What is false

1. **"Permanently."** What is permanent is the shape; what the case demands changes with the case.
   A stored answer is right 1.92% of the time it fires, and the stored answers that are right on
   unseen programs are the ones that carry almost no information.
2. **"So it solves everything on a computer."** Addressability saturates at ~60% and the product
   with precision is ~1%. Memory is a residue handler, not a solver.
3. **"It beats how agents learn today."** No: today's agents learn by *training on* experience and by
   being *given instructions*, and the 2026 measurements above say instruction is worth 4× a lived
   experience. Our memory numbers land in the same range as everyone else's — the reason to build it
   is that it costs 41 µs and no parameters, not that it is stronger.
4. **"One trace is enough."** Already measured in this tree: a single trace fits exponentially many
   hypotheses (`INSUFFICIENCY_CERTIFICATE_20261113_V1`); one demonstration removes at most
   `log2|Y|` bits (1.74–5.36 measured) whatever the hypothesis space is (`THE_FOUR_LEVERS…`).

## The single bottleneck, now with the arithmetic that decides it

> **The interface: can the fact the goal depends on be *asked for* at the moment of acting, and
> answered by the artifact itself?**

The learning law this tree derived is
`bits_after = log2(|H|/|G|) − I(E) − Σ I(q) − I(interface)`. Today's numbers put a value on each term
for the first time on the same task set:

- one **experience** `I(E)`: ≤ `log2|Y|`, measured 1.74 bits each further demonstration;
- memory of experiences: **0.597 × 0.0192 ≈ 1.1%** of unseen decisions;
- one **asked question** `I(q)`: **1.0 bit** when chosen, 0.15 when not, at **7.69 ms**, and *exact*
  when the artifact answers — it closed 3 of 14 bugs no rung of this tree had ever repaired;
- the **interface** `I(interface)`: the only term that can be made arbitrarily large at zero marginal
  cost, because it is the artifact itself — the program, its tests, the live environment.

Observability binds computer use (4.814%; near-zero past two hours on OSWorld 2.0). Expressibility
binds coding (3 of 9 answerable bugs had no site that could build the value the case demanded).
They are the same term.

## What is actually smartest to build next — and why it is not "a better memory"

**Store the question, not the answer.**

A stored *answer* is a claim about the world that decays with the case (1.85% precision). A stored
*question* — this shape of site owes a value of this kind, and the case will tell you which — is
invariant (it survives renames, which destroyed 7/10 of the memory wins) and its answer is verified
at the site, so it cannot be wrong: it is either answered or refused. The table's job becomes
*compressing the search*, not replacing the oracle.

Concretely, in the only order that pays:

1. **Question table.** Fill `shape → which value the failing case demands` over the corpus, and
   measure questions-to-fix against the measured baseline (75, 679, 920 questions per bug). This is
   the one place where a finite table (≤153 rows here) collapses a search into a handful of exact
   questions, and it is the only path that keeps both addressability and exactness.
2. **The same instrument on a real repository**, where the interface is a compiler and a test suite
   and the tasks are SWE-bench ProMax-shaped (11.4 files, 261.6 lines). Nothing in this design is
   corpus-specific; the site becomes a location in a repository and the value demanded becomes a
   failing test's expectation.
3. **Parameters stay a computation, not a library.** Every bit the model holds must be *calculated*
   from the artifact at hand — the interface supplies the knowledge, and the table supplies the only
   thing worth remembering: which question to ask.

A sentient creature is not the one that has remembered the most actions. It is the one whose
*questions are chosen* about the part of the world it cannot yet predict — and the measurable proxy
for that is bits removed per interaction: 1.0 for a chosen question, 0.15 for an unchosen one, 1.74
for a whole lived demonstration.

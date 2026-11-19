# The goal is a quotient of the trace

**2026-11-28 · branch `arena/46dde2a5-brain` · receipt `canonical/verification/THE_GOAL_IS_A_QUOTIENT_OF_THE_TRACE_20261128_V1.json`**

---

## 1. The question, and the object it was hiding

*Instant learning is perfect, and instant learning in a new environment is perfect; so give the model the
most advanced coding actions once, let it experience them, and everything on a computer is solved —
permanently. Is that right?*

Last round answered the goal's *history*: a goal cannot be a function of the final state. But the terms
of that answer — `created_once`, `two_copies`, `never_together`, `precedence` — were **written by me**.
Which means the measurement could only ever say "the vocabulary I supplied works". That is the same sin
this project keeps finding at every level: a handed-in object wearing a measurement's clothes.

The object underneath is smaller and sharper. A reading of the machine after every step is a tuple of
rows `(identity, content)`. **The goal is a function of some statistic of that tuple** — and which
statistic is not a matter of taste. It is decided by the runs the user judges differently.

So the question "what must the agent observe to know the goal" is **computable**, and so is its price.

## 2. What is false in the claim

1. **False: "give it the action once and it learns it".** One experience gives the *effect* of an action
   in the state it was tried in. It does not give the statistic the goal is about. The number of
   experiences the goal costs is the number of cells of that statistic — measured here as **3 to 5** —
   and 3 is not 1.
2. **False: that the goal is about the action.** On one machine, two goals need *different* statistics,
   and each is provably blind to the other (F2): the statistic, not the action, is the unit.
3. **False: that the observable is a matter of design taste.** It is chosen by the data. FILESYSTEM's
   sentence is carried by the count history of one content; the "moved, not copied" sentence is not.
4. **False: that a sufficient statistic is sufficient.** A statistic chosen on one- and two-action runs
   collides **208 times** on three-action runs (F5). Sufficiency is relative to the run set it was
   measured on. This is the round's most important failure and it is reported as one.
5. **False: that any of this is sentient.** It is an identification machine that can now state what it
   does not know and what knowing it would cost. Sentience is not measured here and is not needed for
   any claim above.
6. **False: that any of this is coding capability.** Three CLI machines, no display, no synthesis. What
   improved is the *price of a goal*, not the ability to reach one.

## 3. The measurement

Three real machines (`sh`/`mv`/`cp`/`rm`, `sqlite3`, `tar`), every action sequence of length 1–3 executed
from a fresh reset, the machine's own reader sampled **after every step**, runs deduplicated by trace.

Four rungs of supplied structure over the *same* reading, each a strictly larger family of statistics:

| rung | what it contains |
|---|---|
| `raw` | the whole trace — one cell per run |
| `fields` | the reading's ten own fields (final rows, contents per step, identities per step, deltas, change events, content→identities, identity histories, …) |
| `literal` | the same fields aimed at the literals the machine actually emitted (`count_trace[c]`, `holders_ever[c]`, `content_by_step[i]`, …) |
| `derived` | a fixed small algebra over a literal: `increments[c]`, `decrements[c]`, `two_copies[c]`, `present_throughout[c]` |

For every goal the round computes, over every projection of one or two generators: its **image count**
(the cells), whether any two runs with opposite judgments collide, and the coarsest sufficient one. For
every projection *cheaper* than the winner, it emits a **witness pair** — two runs with the same image and
opposite judgments. That pair is the proof that the cheaper observable cannot carry the goal.

## 4. Results

**The price of a goal in experiences** (coarsest sufficient statistic, cells):

| goal | runs | `raw` | `fields` | `literal` | `derived` |
|---|---|---|---|---|---|
| "the content arrived once and was never removed" — FILESYSTEM | 68 | 68 | 55 | 19 | **5** |
| the same sentence — SQLITE | 48 | 48 | 7 | 7 | **4** |
| the same sentence — TARBALL | 32 | 32 | 7 | 7 | **3** |
| "moved, not copied-then-deleted" — FILESYSTEM | 68 | 68 | 56 | 24 | **6** |

The top rung's winners:

- FILESYSTEM: `increments[probe_new] ∧ decrements[probe_new]` — 5 cells, **every cell pure**.
- SQLITE: `increments[probe_new]` — 4 cells.
- TARBALL: `holders_ever[probe_new] ∧ decrements[probe_new]` — 3 cells.
- the "moved" goal: `contents_ever[copy] ∧ increments[probe_old]` — 6 cells. **Not** the portable
  goal's statistic, and the portable statistic has witness collisions on this pool (F2 MET).

**One sentence, three machines, one observable.** Seven single statistics suffice for the *same*
sentence on all three machines — including `count_trace[probe_new]` and `count_delta[probe_new]`. The
observable transfers with no measurement of the environment; only the table is refilled (F1 MET).

**A goal the reading cannot see, and the repair.** "The listing atom ran": `[FS_A1, FS_A1]` and
`[FS_A1, FS_A5]` read **identically at every step** and the user judges them oppositely. No projection,
at any rung, separates them — 0 sufficient projections out of 1 + 55 + 903 + 2 485 (F3). Adding one
generator the machine already exposes — the executor's own call log — makes the goal learnable at **30
cells**, one per sequence. The repair is real, and it is expensive; both are reported.

**The failure that matters.** Choose the statistic on the depth-2 pool, then ask it to carry the goal on
the depth-3 pool: **208 colliding pairs** (F5). The shallow pool never contains "add it, then remove it",
so the statistic that looked sufficient is not. Sufficiency is **reachability-relative**.

**Score, declared before the run:** F1 MET · F2 MET · F3 MET · **F4 NOT MET** · **F5 NOT MET** · F6 MET.
23.7 s, 0 parameters, 0 model calls.

## 5. The two criteria that failed

**F4 declared "at most four cells at the top rung". FILESYSTEM gives five.** Not a rounding: the five
are the observed `(increments, decrements)` pairs. The estimate was mine, the number is the machine's,
and the criterion stays missed rather than moved. The substantive claim — that the ladder buys cells at a
measured exchange rate and that the top rung's table is pure — holds.

**F5 declared that the statistic chosen on the shallow pool would have no collision on the deep pool. It
has 208.** This is the honest shape of the whole project: every "sufficient" is sufficient *for the runs
that were executed*. Deeper runs are not a bigger sample of the same thing; they are new cases, and one
of them (add-then-remove) is exactly the case that separates a goal from its near-miss. The number of
cells is therefore a price *given a run set*, never a property of the goal alone.

## 6. The law

> **A goal is a quotient of the trace. Its price is the number of cells of the coarsest sufficient
> statistic, and that number falls with the structure supplied and rises with the depth of the run set
> it is measured on. The statistic is chosen by the data and proved minimal by witness; it is never
> proved sufficient in general, only for the runs that exist.**

Two consequences, both measured:

1. **Learning is finite and permanent once the statistic is in hand** — `k` cells, `k` experiences, then
   a table (3–6 here, against 20–68 distinct runs). This is the precise content of "learn it once, keep
   it forever", and it is why one experience is not it.
2. **The statistic is the remaining supplied object.** The coarsest function of the trace is the label
   itself — two cells — and it is unlearnable; the raw trace is 68 cells and teaches nothing. The ladder
   is the trade-off, and the trade-off is the frontier, not a detail.

## 7. What is real and what is not

**Real:** the cells at every rung on every machine, the purity of the top tables, the seven shared single
statistics, the two blind-to-each-other statistics with witnesses, the identical readings of two
differently-judged sequences, the 208 collisions, the 30-cell repair, the zeros and the 23.7 s.

**Not real / not claimed:** the generator families are typed by the reader's structure and its literals —
a smaller supplied object than a predicate grammar, but supplied; projections are enumerated up to two
generators; the tables are per environment; three CLI machines are not computer use; nothing here
synthesises or plans; and the run sets are three actions deep, which F5 shows is exactly where the claim
gets weak.

## 8. The single bottleneck

Identification is cheap (5–6 questions, previous round). The observable is now computable (this round).
What remains is the thing both of those are *relative to*:

> **The run set you can afford to execute. It fixes which statistic you are allowed to believe, and
> therefore what your goal costs.**

F5 is that sentence with a number: a statistic sufficient on 30 shallow runs collided 208 times on the
68 deeper ones. At this frontier the run set is enumerable in three actions. On a real codebase or a
screen it is not — you cannot execute every edit sequence, and the runs you can execute are exactly the
ones that decide whether your statistic is right. So the bottleneck is not the goal, the vocabulary or
the question. It is **producing, at the frontier, the runs on which a statistic can be falsified** —
which is the synthesis half, unchanged, now with a sharper reason: every rung of this ladder is only as
true as the deepest run in it.

## 9. Next step, and what would falsify this

Next: take the ladder to a run set that is **not** enumerable — a real task in this repository's own
hardest open material — and measure the cheapest statistic that survives a *held-out depth* rather than
a held-out run, pre-registered: zero collisions on the deeper pool, the cell count, and the number of
runs it took to find the colliding pair.

Falsifiers of this round: a cell that is not pure at a rung where the statistic was called sufficient; a
winner that names a statistic `generators_for_rung` did not produce; F4 or F5 reported as met; the
"moved" goal separated by the portable goal's statistic; the two sequences above reading differently.

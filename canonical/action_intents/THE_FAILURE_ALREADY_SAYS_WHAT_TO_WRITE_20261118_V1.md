# The failure already says what to write

*2026-11-18 · measurement: `canonical/verification/THE_FAILURE_ALREADY_SAYS_WHAT_TO_WRITE_20261118_V1.json`
· tool: `canonical/tools/force_the_value_and_see_v1.py` · corpus: QuixBugs @ `4257f44b`*

## The question, restated so it can be answered

> "We solved instant learning in new arbitrary environments. Doesn't that make everything else
> unnecessary? Give the model the most advanced coding actions, let it experience each once, and it
> owns them permanently."

Two sentences are hidden in that one. The first is about **actions** (a capability, once shown, is
kept). The second is about **coding** (a repair, once shown, is kept). They are different claims with
different walls, and this tree has now measured both.

## What is true

**1. A failure is a specification, not a verdict.** This run asks a question, one run per question:

```
force the expression E at site s   ->   run the failing case   ->   did it pass?
```

That is the whole mechanism (`force_the_value_and_see_v1.py`). There is no edit-kind list, no
candidate space of programs, no model, no network, no answer key. It is complete for the class
"one expression at one site replaced by one expression", because forcing *is* that replacement —
the hook evaluates the candidate in the site's own frame, so the run is the patched program's run.

**2. It is 450× cheaper per candidate than judging programs, because it never runs the test suite.**

| | per candidate | what it answers |
|---|---|---|
| force an expression at a site | one run of **one case** | does this expression make the failure pass |
| enumerate a program and run pytest | one run of **the suite** (3.5 ms) | is this program accepted |

Measured this run: **14 published bugs, 15,759 questions, 121.2 s, 7.7 ms per question** — and the
7.8 ms is dominated by building the candidate list, not by asking.

**3. Three bugs no rung of this tree had ever repaired were repaired, and none of them was repaired
by the published fix's text.**

| bug | question budget | fix the case asked for | is it correct beyond the cases |
|---|---|---|---|
| `get_factors` | 920 | `range(2, 1 + n)` | yes — trial division that always finds a factor |
| `kth` | 75 | `pivot = max(arr)` | yes — `above` is always empty, so the mis-indexed call is never taken |
| `mergesort` | 679 | `if len(arr[1:]) == 0` | yes — recursion stops at one element |

Each is an *independent* correct fix, not a paraphrase of the published one. The search found the
semantics the failing case demanded; it did not find the answer key. `kth` (75 questions, 0.5 s) and
`mergesort` (679 questions, 11.7 s) were repaired with the failing case *raising* rather than
answering wrong — the case still said what it wanted, because the value changes control flow.

**4. Instant knowledge is real but it is not the whole solver.** 40/40 published QuixBugs bugs,
zero execution, zero model, zero network (previous receipt, `WHAT_IS_LEFT_FOR_A_LESSON_TO_BUY`):
**18/40 need no lesson · 8/40 reachable through a taught class · 3/40 (7.5%) transfer to a program
the lesson was not taught on · 13/40 need an edit no class in the tree can build.** A lesson is worth
3 of 40. Knowledge that is *recorded* is cheap and permanent; knowledge that is *transferred* is
narrow. Both facts are true at once.

## What is false

**False: "experience each action once and it is owned permanently."** Owning an action is not the
problem. The wall for computer use is **observation**: 4.814% of the benchmark's facts can be
observed at the moment of acting, and OSWorld 2.0 falls to near zero past two hours because what the
goal depends on stops being visible. An action you cannot see the result of is not owned, however
many times you performed it.

**False: "the failing case tells you the program."** It tells you *a value*. This run measures how
far that goes: of the nine bugs that had published cases and a calibrated judge, **three were solved
by one expression at one site**, one exhausted its budget, and **three were not fixed by any
expression the site's own material could build** (`lis`, `next_permutation`, `possible_change`). A
case can demand a value; it cannot supply the expression that produces it.

**False: "one trace identifies the program."** The trace fits exponentially many hypotheses — the
identifiability result already in the tree (`INSUFFICIENCY_CERTIFICATE_20261113_V1`). That is why the
question has to be asked against the case and not inferred from the trace.

## The single bottleneck, now measured rather than argued

> **The failing case names the value it wanted. The question that decides everything is whether the
> artifact can express that value at the site where it is needed.**

Observability binds computer use; **expressibility** binds coding. This run turned that from a claim
into an arithmetic: 3 sites in 3 bugs could build the demanded value; 3 bugs had no site that could.

And the two walls meet in one place: **the expression a site could not build is exactly the thing a
lesson is for.** The 3/40 transfer number and the 3/9 repair number are the same number seen from two
sides — the vocabulary is the bottleneck, and vocabulary is bought by *recording*, not by searching.

## The smartest path to fixing it (not a primitive one)

Every repair this tool performs already contains the answer to the vocabulary problem and throws it
away: **the site's demanded value, and the expression that produced it.** Recording that pair, keyed
by what the site is (its operator, its operands' shapes, the value demanded), turns one repair into
one permanent fact:

```
(site shape, value demanded)  ->  expression that produced it
```

- zero parameters — it is a table, not a weight;
- instant — a lookup, not a search;
- additive — the same table answers the next bug that demands the same value at the same shape of
  site, which is precisely the 3/40 that transfer today;
- and it grows the vocabulary exactly where the grammar fails, which is where the failures are.

The next build is therefore not a better search. It is: **run the tool on the whole published corpus,
keep every (site shape, demanded value) → expression pair it proved, and let the table — not a search
— answer the next failure.** The search exists only to fill the table; the table is the knowledge.

That is the same law the tree already obeys: the best part is no part. No model, no weights, no
candidate space — a table of facts the corpus itself certified.

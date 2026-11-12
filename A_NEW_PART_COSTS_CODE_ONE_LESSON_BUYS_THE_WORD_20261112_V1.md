# A new part costs code; one lesson buys the word

**2026-11-12.** Base `c4724d90`. Branch `arena/9914f9a5-brain`. Round 9 of today's series —
and the round that executes round 8's prescription instead of restating it.

Round 8 ended with the instruction: *grow the operator space deliberately, and pay for it in code*,
and proved the negative half — no demonstration can teach `median` while no part expresses it.
This round buys the operator, once, and measures every step of the loop the owner keeps asking for:

> *Give the model the smartest actions, let it experience each once, keep what it learned — so we
> solve everything on a computer, perfectly and permanently. Can't we do this now?*

**Answer in one sentence: the loop works, and this round prices it — an action costs a part in
code (14 → 15 parts, 400 → 560 operations, two files, ~10 lines), after which one lesson teaches
the word permanently, answers five requests nobody showed, and is re-checked by a gate that can
still say no; what you cannot do is buy the part with experience, which is exactly where
"one try in every environment" stops paying.**

Authority **NONE**. Producer-run, one machine, no independent personnel. `truth.achieved` stays
`false`. $0, zero model dependency. Every number below was produced on this commit.

---

## 1. The measurement, with the predictions written first

Pre-registered in the probe's docstring before the first run:

| # | prediction | result |
|---|---|---|
| 1 | Under the old algebra the median lesson is set aside — no operation fits its two example answers | **held** — `NO_OPERATION_I_CAN_PERFORM_GIVES_THESE_ANSWERS`, 0 of 400 operations fit |
| 2 | After one reducer is added in code, the SAME lesson teaches exactly one word | **held** — taught, `{"median": ["median"]}`, nothing else added |
| 3 | Five held-out requests — a file in no lesson, the seed's own number files, and a `median`+`rest` composition no lesson shows — are answered correctly, against expected values written down before the run | **held** — 5/5 correct, 0 wrong |
| 4 | The independent checker accepts an honest median claim and rejects the upper median on the same file | **held** — accepted; rejected with `claimed=20:recomputed=30` |
| 5 | `mode`, which no part can express, is still refused by name after the lesson | **held** — `UNKNOWN_WORD:mode` |
| 6 | No seed word changes meaning; `median` is the only addition | **held** — 0 harmed |
| 7 | Clear the cache; the stored lexicon alone still answers | **held** — 143 from disk |

And the end-to-end case, through the live door with its own recomputation gate
(`taught_program_recomputed`, the only predicate in the registry that re-runs what it learned):

```
teach "what is the median number in n.txt" (2 example files)   taught=True
ask  "what is the median number in <world>/nb.txt"             pass=True, answer=9
ask  "what is the mode number in <world>/nb.txt"               refused, names the word
provenance re-run after the change                             39/39 checks,
  producer vs checker agree on every operation                 5600 comparisons, 0 disagreements
```

The cost of the action, which is the number the owner's plan needs:

```
parts                      14 -> 15          (the docstring and the registry limitation
                                              said "fifteen" while PARTS held fourteen;
                                              the prose is now true)
operations                 400 -> 560        (+160: one reducer × every unit/filter/measure
                                              combination the algebra allows)
runtime files touched      2  (taught_words_v1.py, taught_words_check_v1.py)
lesson that buys the word  1 sentence, 2 example files, whole-number answers
```

Two things were *not* changed, on purpose: the seed lessons and the seed lexicon (both pinned by
the capability's receipt), and the true-suite generator (it does not emit `median` questions —
so `median` is covered by the probe's three-way agreement and the new tests, **not** by the true
suite; extending the generator is unclaimed work). The receipt was re-run and re-pinned: 39/39.

## 2. What this settles about the owner's sentence

**"Let him experience them once and then he learns them."** For a *word* over an *existing*
algebra: yes, and now at a measured price — one lesson, two examples, permanent, composable,
reload-safe, re-verified at recall. This is the third independent demonstration in the tree that
the loop is real (round 8's `records`; this round's `median`; the earlier cross-machine carry).

**"The most advanced coding actions."** Actions are parts. This round shows what adding one
actually is: an enumerable form, an independent recomputation, a refusal outside it, ~10 lines in
two files, then re-pin the receipt. That is cheap — but it is *code*, and no amount of experience
produces it (prediction 1: the lesson itself was refused before the part existed). Round 8 said
this in prose; it is now a priced procedure.

**"So we solve everything on a computer, permanently."** The quantifiers still fail, and this
round does not move them. What moved: the cost of one more slice of "everything". What did not:
identification (one demo leaves 14 of 47 candidates standing — round 2), applicability (one
success identifies 0/200 requirements — round 4 of the owner's question), cross-kind compounding
(1525 vs 1525 environment calls — measured twice), and reach (the front door reaches 8 of 149
bound capabilities). Nothing here contradicts any of those; the algebra grew by one reducer.

## 3. Scorecard: real vs wrong, as of this commit

| claim | verdict | where it was measured |
|---|---|---|
| A lesson persists across restart and is re-verified at recall | **TRUE** | rounds 1–8; this round's prediction 7 |
| One lesson teaches a word that composes with everything known | **TRUE** | round 8 (11/12 held-out), round 9 (5/5) |
| One try transfers to a new instance of the same kind | **TRUE ~half the time** | 8/15 one-trial, 6.33× mean, 0/15 worse |
| Experience compounds inside a family | **TRUE, first measured instance** | period-12 armed 59 → 35 questions (41% fewer), rounds 23–24 |
| One try identifies which rule | **FALSE** | 10% leader-correct, 0/10 exact; 2 *chosen* questions → 10/10 |
| A success teaches when the action applies | **FALSE** | 0/200 identified; the general survivor says "always" in 68% of failing states |
| More environments make the next kind cheaper | **FALSE, twice** | 1525 = 1525 byte-identical; learning-to-learn 3/10 vs a coin flip |
| Experience can add an operator | **FALSE, now by construction** | prediction 1 this round: the lesson was refused until code added the part |
| The gate would keep what is learned | **TRUE for 9 repair caps, FALSE was the defect** | 8/8 failures rejected after #6678/#6680; the ninth was repointed on main while this round was in flight -- re-measured here: DEFINITE = 0 |
| "Everything on a computer, perfectly, permanently" | **CATEGORY ERROR** | 8/149 reachable; RLI failures 45.6% *quality*; OSWorld failures *verification* |
| It is becoming a sentient creature | **NOT MEASURED, NOT THE OBJECTIVE** | the only measurable half — experience changes competence on new problems — is negative across kinds |

**Measured where nobody here wrote the task** (PR #6681, receipts landed today, no prose yet —
read here first): on the 40 QuixBugs programs, the organ stores 22 fixes and re-repairs the same
bug **22/22** — and buys **1/40** on other bugs as taught, **3/40** with every transfer knob
open. On 100 HumanEvalFix bugs, lessons from other fixes repair **62/100**; the control shown the
same changes *backwards* repairs **56/100** — the lessons' own contribution is **+6**. On 500
SWE-bench Verified tasks, operators reproduce **2103/2178 (96.6%)** of a task's own edit pieces
but **1638/2178 (75%)** are never seen on other tasks. On 130 MiniWoB pages in a real browser, one
success yields ≥18/20 held-out on **45** tasks (replay alone: 0; random: 0) — and a single shared
library of everything learned does first-sight work on **24** tasks, "transfer reaches relatives of
what was learned and no further". Real code, real pages, same shape as the toys: **reuse where
structure is shared, near-zero where it is not.**

## 4. The external state, refreshed 2026-11-12 (max web, latest first)

- **Continual-ARC** (Lenton, arXiv:2611.14505, 10 Nov 2026 — two days old): three shipped agent
  harnesses (OpenClaw, Hermes, Prime on GPT-6 Luna) save **no measurable spend** on puzzles they
  have already solved; only weight training moves unseen tasks (**49/100 vs 19/100** for a 9B).
  Abstract: *"No harness-based method gains on unseen tasks, whereas weight-based learning shows
  substantial gains."* This is the tree's own cross-kind negative, reproduced externally on
  frontier harnesses — and it is the strongest reason the prior (lever 1) is the ceiling. Under
  Brain's law the weights route is closed at runtime; it leaves the acquisition-time distillation
  route (Program C) as the legal way to grow what harness memory cannot.
- **Remote Labor Index**: 2.5% (Oct 2025) → 16.1% (Jul 2026) → **41.3%** for Fable 5.2 (reported
  11 Nov 2026; secondary sources — treat the last number as provisional). Even at 41%, the
  largest failure bucket is *"fell short of expert quality"* — completion, not clicking.
- **OSWorld 2.0/2.1**: at release the best was 20.6% binary (Opus 4.8); the leaderboard now shows
  Opus 5 at **44.33% binary / 77.67% partial** (Snorkel, 29 Oct 2026). Named failure modes:
  losing constraints, missing mid-task information, guessing instead of asking, **skipping
  verification** — applicability and completion, not action execution.
- **CLE** (arXiv:2610.33956, 25 Oct 2026): best system (Claude Code + Opus 5) clears **47.7%** of
  levels and **23.3%** of full task ladders; feedback + one revision buys a median **+5.3 pp**.
  Sustained learning from experience is the measured gap, at the frontier, with weights frozen.
- **Agent S4** (arXiv:2610.28601, 20 Oct 2026) still stands as the year's move: evolve the
  *interfaces*, select on held-out validation → 3.8× on OSWorld V2 with the same 27B model. It
  pays for identification; it does not get it free from exposure.
- **SEAL / verifier–deployment gap** (arXiv:2607.24300): self-scores stay near 1.0 while
  deployment collapses; the fix is a sealed, harness-side accept/reject the agent cannot write.
  This tree's gate series (rounds 4–8) is the same discovery, applied to its own registry.

Nothing published since the last round *helps* the owner's quantifiers; everything published since
confirms the architecture (frozen weights, harness learning, verifier gates, evolved interfaces)
and refutes "one try → permanent → everything".

## 5. The limiting factors, ranked, and the smartest next moves

From first principles there are three levers — coverage of the hypothesis language, selection of
evidence under it, honesty of acceptance — plus one multiplier (reach). Ranked by expected change
in what the system can *conclude*:

1. **Grow the operator space, per the template this round just priced.** Every remaining capability
   the owner names is a part: a new action, a new query shape, a new refactor. Cost now known:
   ~10 lines + independent recomputation + re-pin (39/39). *Kill:* a part whose recomputation
   cannot be written independently is not a part — refuse it like `median` refused before it
   existed.
2. **Record failures as evidence** (`macro_v1` currently spends refusals on a counter). One
   failure deletes the "always applicable" survivor — the only update that can (0/200 → 25/25).
   Small change to an existing organ; without it, applicability stays unlearnable by construction.
3. **Make the 11 BLIND premises decidable** (a `git` probe, an HTTP probe, a PyPI read): 10
   registered capabilities are currently uninvocable for a reason the system cannot name. Bounded,
   verifiable, measured — the highest capability-gain-per-hour item that is not research.
4. **Widen the interface regime** (the Agent S4 move, in-tree form): express GUI/document work as
   code against a declared contract with a mechanical check. One-shot transfer is free inside that
   regime; this round's loop is the template for everything outside it.
5. **Second compressive family + admitted abstractions as search primitives** (rounds 23–24's own
   next step): the first family proved cross-instance compounding exists (41%); one more family
   decides whether the *mechanism* generalises or the round was a family trick.
6. **Then, and only then, B1 — donor-distilled hypothesis spaces** (acquisition-time, donor
   deleted, verified at zero model): the only route to a shared prior no person wrote, and the
   only answer to Continual-ARC's finding that harness memory cannot.

**Explicitly not on the list, each already measured and failed:** breadth of environments as a
strategy; more exposure per lesson; more stored skills without a shared space; sentience as a
target; opening the 226-refusal execution gate to make a red count green; runtime donors.

## 6. On "a sentient creature"

Keep the measurable half — *experience changes competence on new problems* — and keep it as the
target it already is. Today's honest reading: experience changes competence **within** a kind and
**within** a family (8/15; 41%), composes words over a fixed algebra (11/12, 5/5), and does not
yet move across kinds (0/10; 3/10). The word "sentient" measures nothing here and makes every
honest number sound like failure. Drop the word; keep the target; the scorecard above is its
instrument.

## 7. Receipts

```
python3 operator_space_growth_median_20261112.py --list
    14 -> 15 parts, 400 -> 560 operations, lesson refused before / taught after,
    5/5 held-out correct, mode refused, checker two-sided, reload ok
python3 -m pytest -q canonical/tests/test_operator_space_growth_median_v1.py \
                    canonical/tests/test_one_lesson_buys_a_word_not_an_operator_v1.py \
                    canonical/tests/test_taught_words_answer_at_the_front_door_v1.py
    28 passed
python3 canonical/runtime/verify_taught_words_provenance_v1.py --write
    39/39 checks passed; receipt re-pinned (producer vs checker: 5600 comparisons, 0 disagreements)
```

Two honest edits to round 8's pins, made in the open: its unteachable example moved from `median`
to `mode` (the pin's meaning would otherwise be corrupted — `median` now has a part), and its
`len(PARTS) == 14` assertion became 15. Also fixed while here: round 8's "wrote nothing into the
tree" check pointed at `canonical/canonical/...` and passed vacuously; `ROOT` is now `parents[2]`
and the check is real.

## 8. Non-claims

One algebra (file questions), one new reducer, one lesson, five held-out requests. No capability
registered, no family flipped, no true-suite coverage for `median`, seed lessons and lexicon
byte-identical, no live state written into the tree, no independent personnel verification, no
benchmark movement, no GUI, no claim about models or sentience. `truth.achieved` stays `false`.
$0, zero model dependency.

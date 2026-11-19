# Coverage is the bottleneck, not hypotheses

*Round dated 2026-11-19. Receipt: `canonical/verification/COVERAGE_IS_THE_BOTTLENECK_NOT_HYPOTHESES_20261119_V1.json`.
Tool: `canonical/tools/coverage_is_the_bottleneck_not_hypotheses_v1.py`. Tests: 11, all green. Nine real actions,
36 real states, 17 facts, 486 measured executions, 4.6 s. No model, no parameters, no network.*

---

## 0. The open thread this closes

`INSUFFICIENCY_CERTIFICATE_20261113_V1.json` is the receipt the question names, and its last word is a bound:

```
closed_vocabulary_size 31   hypotheses_that_would_need_enumerating 8_388_608   learner cap 12
BOUNDED__TOO_MANY_CANDIDATE_FACTS_TO_ENUMERATE
"absence removes the separation obstruction but not the enumeration bound, so the obstacle moves
 from representation to combinatorics"
```

The previous round here measured that *one refusal per coordinate* identifies a precondition 10/10 where 160
state observations identified 0/10. Both cannot be the whole story. If cuts identify, then `2^23` is not the cost
of identification — it is the cost of *enumerating*, and nothing in an agent's life requires enumerating.

This round measures which the wall actually is, on one machine, with every outcome measured by running the real
binary in a real tree:

| n = 17 facts | count |
|---|---|
| candidate subsets of facts | **131 072** |
| candidate conjunctions, with polarity | **129 140 163** |
| the certificate's open bound at 23 effective facts | 8 388 608 |
| most executions any action needed for identification | **24** |

Nine actions × 36 states = 486 executions. Zero hypothesis lists written down.

## 1. The schedule in the question decides almost nothing

Schedule A is the charitable form of *"let it experience each action once"*: one success, plus the two refusals
nearest to it. A survivor set is a rule only where it is **unanimous**; where it is not, it is undecided, and this
round scores undecided as undecided instead of assuming it away.

| action | A: executions | survivors | of 12 held-out states |
|---|---|---|---|
| `git_stash_pop` | 3 | 5 120 | **12 undecided, accuracy 0.000** |
| `tar_x` | 3 | 6 144 | 10 undecided |
| `rmdir_dir` | 3 | 5 120 | 9 undecided |
| `cp_a_into_dir` | 3 | 4 608 | 8 undecided |
| `patch_apply` | 3 | 4 096 | 8 undecided |
| `sort_c` | 3 | 5 120 | 9 undecided |

The one-try schedule does not produce a *wrong* answer. It produces **no answer**: thousands of rules remain, and
they contradict each other on almost every state it has not seen. `accuracy_of_the_set` never exceeds 0.917 and is
0.000–0.333 for seven of the nine.

## 2. What actually removes the survivors: successes, not refusals

Last round concluded "a success teaches nothing". That was true of a *single base state* and it is false in general,
and correcting my own claim is the point of this section:

> A fact that holds in **every** success can always be conjoined to the true precondition without contradicting
> anything: the coordinates are true in every success, and every refusal violates a coordinate, so a superset is
> never a subset of a refusal. Therefore **only a success in which the fact is false can eliminate the superset.**

So successes are not wasted information — they are the *only* evidence of irrelevance. Adding the varied successes
collapses the space:

| action | A survivors | B survivors | B held-out |
|---|---|---|---|
| `git_stash_pop` | 5 120 | **2** | 1.000 |
| `cp_a_into_dir` | 4 608 | **2** | 1.000 |
| `rmdir_dir` | 5 120 | **4** | 1.000 |
| `gzip_x` | 4 096 | **4** | 1.000 |
| `sort_c` | 5 120 | **4** | 1.000 |
| `patch_apply` | 4 096 | **4** | 1.000 |

6 of 9 actions are exact on held-out states after at most 24 executions. The price is not `2^17`; it is
`1 success + k refusals + one success per fact that must be shown irrelevant`.

## 3. The three that stay undecided, each for a measured reason — and never wrong

The failure mode is the important part, and it is the opposite of the one everybody fears:

```
exact on held-out:       6 / 9
undecided:               3 / 9   (ln_link 1024 survivors, mkdir_nodir_sub 1024, tar_x 6)
confidently wrong:       0 / 9   on every held-out state of every action
```

The three are named, not averaged:

- **`ln_link`, `mkdir_nodir_sub` — coverage.** Their seen successes never falsify a handful of facts
  (`btgz_valid`, `dir_empty`, `dir_exists`, `xgz_valid`, …), so 1024 supersets survive. This is exactly what the
  coverage law predicts, and it is what an agent that has not yet varied those facts *should* report: undecided.
- **`tar_x` — soundness of the column.** It has full coverage and still abstains on one held-out state, because its
  fact `btgz_valid` is computed with `tar -tzf`, and last round measured that `tar -tzf` **returns 0 for a gzip whose
  payload is not a tar archive**. The column does not mean what it claims, so the rule built on it is not entailed by
  the world. A cheap check is not a fact.

That gives the round's symmetric law:

> **A rule is exactly as good as (a) the facts that vary in the data it has and (b) the checks that compute them.
> Coverage without soundness is undecided; soundness without coverage is confidently wrong. This schedule's failure
> mode is abstention — which is the only failure mode that is safe to build on, because it says so.**

## 4. Why this is not the combinatorics the certificate feared

The certificate's `8 388 608` is the size of the hypothesis *space* under one particular representation: conjunctions
of facts, enumerated. Identification never touches that space. It asks a smaller question: **do the observations
separate the survivors?** The answer is bounded by the *states*, not the hypotheses — and the states are chosen by
the agent, one per fact it wants to rule out.

The 2026 statement of this is exact, and it is not from this project: identification from a *contrastive
presentation* requires **"every positive of h must appear in some pair"**, and without such coverage *"no learner can
tell them apart"* — provably, for every corruption budget [1]. A pair that crosses the cut is a refusal. The
positive that must appear in some pair is the fact that must be varied. The certificate's wall was the enumeration;
the real wall is the coverage, and coverage is an **exploration budget**, not a hypothesis count.

## 5. The single bottleneck, restated at the layer it actually lives

Six links are now closed by measurement: the decision to act (a free attempt under a judge); the goal's last bit
(a proof, 983 runs, one equivalent statement); the effect's name (computed signature, 44 cells); the precondition
(one refusal per coordinate, 10/10); composition over measured cells (14/16, 0 prediction mismatches); and now the
combinatorics (coverage-linear, 24 executions, abstention instead of error).

What is left is not a mechanism, and it is not more tries. It is this:

> **The agent must visit states that vary the facts it needs to rule out — and it cannot know which facts those are
> until it has visited them. Coverage is therefore a search over state variations, and its cost is the price of
> exploration, not of learning.**

That is the honest answer to *"why can't we just let it try each action once?"*: one try is one point, and a rule
needs a *contrast*. What one try buys is a table entry that is consistent with thousands of rules and silent
everywhere else. What the same budget buys, spent on *varied* attempts, is an exact rule — measured here on nine
real binaries, with the residue named rather than hidden.

And it says precisely what belongs in our weights: not the facts (instant knowledge holds those, written by probes),
not the rules (a fold over measurements), but the two translations — declaration → operator, refusal → fact — plus
the one thing that cannot be a table: **choosing the next state variation that separates the most survivors.** That
is a computation over the current survivor set, it is checkable, and it is the only place a policy is worth
parameters.

## 6. What is real, what is not

**Real.** 17 facts, 36 states, 486 executions. One success + two refusals leaves 4 096–16 384 survivors and decides
0–33% of held-out states for seven of nine actions. Varied successes reduce that to 2–4 survivors and 1.000 on
held-out for six of nine. The three residue cases are named, one of them by an *unsound* column. Confident error:
zero. `2^17 = 131 072`, `3^17 = 129 140 163`, and the schedule needs at most 24 executions.

**Not real.** "The obstacle is the combinatorics." "A success teaches nothing." "One try per action learns the
action." "A check is a fact." Each is false here for a measured reason, and the correction to my own previous claim
is included on purpose.

**Limits.** One machine, nine actions, 36 states, 17 facts, and a fact vector that is hand-written — the same
bottleneck this round prices rather than solves. The hypothesis language is conjunctions of required facts without
polarity; with polarity the count is `3^n` and the argument is unchanged because nothing enumerates either. The
held-out partition is 12 states per action, so "exact" means exact on those. And nothing here prices *finding* the
state variations — that is the exploration budget, and it is the next thing to measure.

## 7. Next step, pre-registered

**Replace the coverage search with a computed one.** Given a survivor set, select the next state variation that
maximally splits it — a fact whose value is not yet pinned, made true in one state and false in another, with the
action still applying in both. Then measure, on these nine actions:

1. the number of variations needed to reach a *behaviourally unique* survivor set must fall below the number of
   facts whose values are unpinned (today: ≥ 24 executions, unpinned counts of 10–12 in the undecided cases);
2. every chosen variation must be **non-intervening in the sense that matters** — it must not require the action to
   succeed where it cannot, so the choice must be validated by the fact vector before execution;
3. the *soundness* check must run first: any fact whose computing check disagrees with the action's own outcome on
   any state is rejected as a column, so `tar -tzf` would be caught before it poisons a rule.

Falsifiers: if the computed variation never beats an arbitrary one, the survivor set carries no usable signal and
coverage is a lottery; if a variation cannot be realised without an invalid state, the reach of the vocabulary is the
limit rather than the policy; if the soundness pre-check rejects a column that is in fact sound, the check is too
strict and the round's law is one-sided.

---

## Sources

1. *Contrastive identification* (arXiv 2605.06211, May 2026) — identification from pairs that cross the cut requires
   every positive of the hypothesis to appear in some pair; without that coverage no learner can separate two
   hypotheses, for every corruption budget. This is the theory under the measurement above.
2. Retained from the merged rounds: OpenAI Frontier Evals' retirement of SWE-bench Verified (23 Feb 2026); *The
   SWE-Bench Illusion*; Leavens & Pigozzi on equivalence versus provability; *Cross-substrate execution identity*;
   *Adaptive state-action abstractions via rate-distortion* (refine when abstraction error dominates); *Agent
   Learning via Early Experience* (error messages as reward-free supervision).
3. Internal, quoted not re-derived: `INSUFFICIENCY_CERTIFICATE_20261113_V1.json` (31 facts, 8 388 608, cap 12);
   `THE_PRECONDITION_IS_NOT_IN_THE_TRACE_20261126_V1.json` (160 states, 0 identified); the previous round's
   refusals (10/10) and its two findings — `tar -tzf` accepts a gzip of garbage, and `git stash list` exits 0 on an
   empty list.

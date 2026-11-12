# What actually blocks the front door, and the work item three of my rounds got wrong

**2026-11-12.** Base `05c9d45f`. Branch `arena/7aa9a777-brain`. Round 8 of the owner's question.

Round 7 ended by naming the next thing worth doing: *"the general collapse of false and unknown
inside `established_facts`"*. Before starting it, I applied the owner's own law — *you sure this is
the smartest approach?* — and asked the question none of rounds 3–7 had asked:

> If I close **every** blind premise, how many capabilities start working?

The answer is **zero**. That is this round's result, and it refutes three rounds of my own work.

Authority **NONE**. One machine, no independent verifier, $0, zero model dependency.
`truth.achieved` stays `false`; no capability registered; no family flipped.

---

## 1. The census

The registry **as the front door actually sees it** — base file, snapshot, and anything the forge
registered — is 155 rows. Each was probed with its own keywords through the real front door and
bucketed by where it died:

| Bucket | Rows |
|---|---|
| **1 SELECTED** (picked and run) | **63** |
| 2 not a candidate for its own keywords | 14 |
| **3 NOT_BINDABLE** (picked, goal cannot supply its arguments) | **61** |
| **4 BLOCKED_BY_UNKNOWN** (a precondition nobody can decide) | **9** |
| 5 BLOCKED_BY_FALSE (the world says no — correct) | 2 |
| 8 no keywords declared | 4 |
| 9 adapter raised | 2 |
| **total** | **155** |

Binding is **61 vs 9**. Six and a half times larger.

## 2. The counterfactual that decides it

A census alone is a list of symptoms. The question is what happens when you remove the thing.
So: assume every undecidable precondition **true**, re-run the same sentence, and see.

| | |
|---|---|
| blocked by a premise nobody can decide | **9** |
| of those, become SELECTED once assumed | **3** |
| of those, then run without an error | **0** |

Of the nine, six do not even become selected — they move to `NOT_CALLABLE_WITH_WHAT_GOAL_PROVIDES`,
i.e. the premise was never their binding constraint. The three that do become selected
(`pypi.provenance.audit_live_artifact`, `source.authority.identity.ror`,
`source.evidence.extract.objective_grounded.stdlib`) all return `ACTION_FAILED`.

**Closing all nine blind premises buys nothing measurable.** Anything built to close them would have
to be defended on grounds other than throughput, and there is a cheaper ground: the sensor is a
sensor, and a machine should be able to answer a question about itself. That is an argument about
honesty, not about capability, and it is a much smaller claim than the one I made three times.

## 3. Why I got it wrong three times

Round 3 measured that the 10 dependent capabilities were *rejected at the perception stage* and
concluded the premise was the blocker. Round 4 revised this downward but kept the item. Round 6
added four rows to it.

The error is the same one in all three, and it is worth naming because it is the most likely error
in any "find the limiting factor" exercise:

> **I measured what stopped a capability FIRST and called it what stops it.**

A blocker is not the first obstacle. It is the obstacle whose removal makes the thing work. The
census finds symptoms; only a counterfactual finds causes. Every round that skipped the
counterfactual produced a confident wrong answer, and the *more* precise the census got, the more
convincing the wrong answer became.

This is now a test, not a note: `test_closing_every_blind_premise_does_not_make_anything_work`
fails if it ever stops being true.

## 4. What this says about the owner's plan

The 61-row binding bucket is where the owner's "give it the smartest actions" plan actually loses,
and round 4 already found the shape of it:

- `git.repository.operate.v1` demands **8** arguments because its template flattens the argument
  lists of seven different operations into one dict. The adapter needs one: measured,
  `run({"op":"log"})` → `output_verified: true`.
- Its own registry row states the intended design — *"the sentence chooses the operation, never the
  argv"* — and the binder asks for the argv anyway.
- `world_binding_v1` and `declared_argument_default_v1` already contain the mechanism
  (`"${input.X | default}"`); the four dispatch capabilities declare no defaults.

So the ranking, by measured count and by whether the fix makes anything *work*:

| Work item | Reaches | Status |
|---|---|---|
| Arity / selector defaults on the 4 dispatch capabilities | up to 4 large ones, and it is the only item with a measured mechanism already built | **next** |
| Binding repair generally | 61 rows | large, needs its own census |
| Blind premises | 9 rows, **0 work after closing** | **deprioritised — measured** |

## 5. What 2026 says

The field has converged on the same ordering from the other direction — the bottleneck is argument
realisation, not missing sensors:

- **Agent S4 / Evolving Agent Interfaces** (arXiv 2610.28601): the gain comes from evolving
  **interfaces and their usage knowledge**, not from adding perception.
- **Life-Harness** (arXiv 2605.22166): *"action realization"* is one of four named recurring
  failure classes, and the harness — not the sensor — is where it is fixed.
- **SkillComposer** (arXiv 2606.06079): the tension is *specification vs generalization* of a skill,
  which is exactly an arity/default question.
- **SkillApt** (arXiv 2609.26863): environment validity should be a **hard precondition** — which
  is round 6's finding, and note that it is a claim about *declaring* conditions, not about sensing
  them.

## 6. Answering the owner

**"What is wrong, why can't we just give it the most advanced actions?"** Nothing is wrong with the
actions. 63 of 155 already run, and round 7 showed the typed door compiles a real multi-step
research task correctly. What stops the other 61 is that the front door cannot supply their
arguments — 8 demanded where 1 is needed — and that is a data/specification defect, cheaper to fix
than any learner, any sensor, or any environment.

**"Am I right or wrong?"** Right about the mechanism and the direction. Wrong about it being a
one-parameter change: the blocker is not "we have not tried enough environments" but "the interface
over-specifies what a call needs". That is the same conclusion the field reached in 2026, and it is
good news — it is a bounded, mechanical fix.

**"Sentient creature."** Not measured, not the objective. This round's only bearing on it is
negative: a system that cannot distinguish "unknown" from "false" *and* that I kept mistaking for
having found its bottleneck — that is a system whose self-report cannot be taken at face value,
mine included.

## 7. Receipts and non-claims

- `what_actually_blocks_the_front_door_20261112.py` — the census and the counterfactual.
- `canonical/tests/test_what_actually_blocks_the_front_door_v1.py` — **8/8**, including the
  refutation itself as an assertion.
- The audit is slow (≈14 minutes) because it runs the real front door over the real registry. A
  synthetic shortcut would measure the shortcut.

**Not claimed:** that bucket 3 rows are badly designed — the sentence may genuinely omit an
argument; the census says where a sentence dies, not who is at fault. Not claimed: that the
counterfactual is exhaustive for the other buckets. It was run only for the unknown-premise bucket,
because that is the one three rounds pointed at. Extending it to all 61 binding rows is the next
measurement, and it is the one that should have come first.

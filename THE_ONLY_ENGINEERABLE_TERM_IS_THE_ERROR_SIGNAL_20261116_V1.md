# The only engineerable term is the error signal — and on real code it misses 46% of wrong edits

*Measured 2026-11-16 on 691 real changed sites from five public repositories, against their real test
trees at the exact commit of each change. Receipt: `canonical/verification/ORACLE_DENSITY_20261116_V1.json`.
Instrument: `canonical/swe_kernel/oracle_density_v1.py`. No model, no synthetic data, no spend.*

## 0. The answer in one line

Experience is not the engine: coverage of real work by memory is 4.8% (`SKILL_RECURRENCE_20261116_V1`),
identifiability is 54.9% and 21.4% for values (`SYSTEMATIC_EDIT_*`), and the third term — whether
anything can tell the agent it was wrong — was never counted. It is now: **45.6% of wrong edits on real
Python work are invisible to the repository's own tests, and 34.2% even when the edit spans two lines.**
Whichever term you cannot engineer is the one that caps you, and it is this one.

## 1. What was counted

For every source site in the pinned corpus, at that commit, in that repository's real tree:

* `has_module_test` — does the changed module have a test file of its own name (`pkg/mod.py` →
  `test_mod.py`, and the old in-package `pkg/tests.py` layout is recognised too);
* `names_a_token` — does the repository's **whole test corpus at that commit** contain a distinctive
  identifier (≥5 chars, not a keyword or builtin) taken from the lines the commit changed.

Both are ceilings: naming is not asserting. A test that names `render` may not check its value — which
is exactly why the number that matters is the product with the *measured* strength of a passing suite,
0.8021 (77 of 96 behaviourally-altered candidates rejected, 19 invisible;
`PATCH_VERDICT_AMPLIFICATION_20261116_V1`).

| population | sites | named by a test | after suite strength (0.8021) |
|---|---|---|---|
| all changed files (incl. docs, CI yaml) | 589 | 0.5042 | invisible 0.5956 |
| multi-line edits, all files | 240 | 0.6167 | invisible 0.5053 |
| **python only** | **330** | **0.6788** | **visible 0.5445 / invisible 0.4555** |
| **python, multi-line** | **128** | **0.8203** | invisible **0.342** |

Per repository the code density ranges from 0.344 (markupsafe) to 0.815 (pyproject-hooks) — the spread
is a property of how the humans wrote their tests, not of the agent.

## 2. The inversion nobody expects

Intuition says advanced, multi-line edits are the hardest to check. **The opposite is true: they are the
best named (82.0%).** Big changes touch public names that tests already mention. The blindness is
elsewhere, and it is in two places:

1. **a third of real Python work** (0.3212) sits in code no test names at all;
2. **a fifth of the named work** (0.1979) is named and still not caught — naming is not asserting.

That second number is corroborated three ways in 2026: *All Smoke, No Alarm* (arXiv 2606.18168) finds
weak or absent oracle signals in **80.2%** of 86,156 agent-authored test patches; UTBoost finds **26 of
500** SWE-bench Verified tasks whose expert-approved tests accept wrong patches; SWE-Bench Pro Verified
(2609.08149) finds **89.2%** of its pass→fail flips were harness exploitation. Checks that exist are not
checks that work.

## 3. Why this decides the whole question

Write capability per action as a product:

```
P(correct) = P(determined) x P(executed) x P(seen)
             = 0.549      x ~1          x 0.545        (code)
             = 0.214      x ~1          x ~0.0         (computer use: no test corpus exists)
```

* `P(determined)` is a property of the **trace**: 54.9%, and 21.4% for the value. Measured, closed.
* `P(executed)` is engineering; it stops being the problem once the action is determined.
* `P(seen)` is a property of the **environment**: 0.545 on real Python, and **zero** wherever no check
  exists — which is all of computer use.

Only `P(seen)` can be engineered. Coverage of memory (4.8%) is a fact about the world; identifiability
is a fact about the observation. So the answer to "give it the most advanced actions once and it has
them": the sample's information content is fixed by the trace, and a campaign of demonstrations moves
neither of the two terms that cap it. It buys the fifth of work that recurs, half of which it gets
right, and leaves the error signal exactly where it was.

## 4. Why this bites hardest exactly where the goal is: computer use

There is no test corpus on a desktop. The observable is whatever state projection the agent builds, and
the 2026 evidence is unambiguous about how that goes: **OSWorld 2.0** (2606.29537) — best configuration
**20.6%** on 108 long-horizon workflows — attributes failure to lost constraints, missed mid-task
information, guessing instead of asking, and **skipping verification**, with **under 7% of budget spent
on detecting and repairing its own errors**, and the worst phenomena being hidden-state recovery and
long-horizon drift. That is `P(seen) ≈ 0` with a diagnosis attached.

So the smartest move for computer use is not more demonstrations and not a bigger model. It is to
**manufacture the missing oracle** from what the environment already gives for free:

* the recorded outcome itself — for replay, intent *is* the recorded consequence, so a differential is a
  complete oracle and needs no human spec;
* content-free invariants — idempotence, reversibility/round-trip, determinism under repetition,
  conservation, commutativity of independent actions. These need no intent either, only the ability to
  act twice;
* state projection diffs — the tree already canonicalises volatile state and projects DOM onto
  predicates (`predicate_world_abstraction_v1`, `htmlform_read_v1`);
* and every manufactured check must first be killed by a mutation of the thing it protects, or it is
  decoration (`property_v1.mutate`, `patch_verdict_amplification_v1`).

## 5. The model we should build, stated as consequences

Nothing here asks for a knowledge house of weights, and nothing here needs one. Given the three-term
product, the model is the smallest object that maximises the third term:

1. **Parameters = the decision rule of the verifier and the search policy.** Every bit computable: the
   acceptance rule is arithmetic on a measured consequence; the search order is a computed ranking over
   hypotheses by expected information. No stored facts.
2. **Facts come from instant knowledge at use time.** Anything lookup-able is looked up — that is the
   project's existing law and these measurements give it teeth: a stored value is a stored guess at 21.4%.
3. **Memory stores guarded plans, never values**: shape + premise to re-check + postcondition to run.
   The measured ceiling for that memory is 4.8% exact, so it is a cache with an invalidation trigger,
   not a belief system.
4. **"Understanding" is operationalised as prediction**: the world model must predict the consequence of
   an action before it is taken, and be corrected by the measured consequence after. A predictor that is
   never corrected is the failure mode OSWorld 2.0 documents; a predictor plus a manufacture-able oracle
   is the only version of "sentient creature" that can be tested rather than asserted — sentience is
   *downstream* of `P(seen)`, because a creature that cannot tell when it is wrong simply becomes
   confidently wrong.
5. **The single control number is oracle density.** Every point of it is capability, multiplied through
   the other two terms. That is the metric to hold the project to, and the receipt now prints it per
   repository.

## 6. The ranked plan, each item framed as a deletion

1. **Delete the demonstration campaign as a capability engine.** 4.8% exact coverage, 0 of 14 on
   multi-line edits: it is a cache warm-up, not learning.
2. **Delete stored values** (21.4%). Recompute under a checked premise.
3. **Delete the parameter knowledge store.** Keep the decision rule and the policy; both computed.
4. **Spend on oracle density first**, in this order: existing suites (0.6788 named here) → differential
   against a recorded outcome → content-free invariants → projection diffs. Then *falsify each check by
   mutation* before trusting it.
5. **Buy senses, not demonstrations.** Measured earlier: 24 of 168 binding cases undecidable with the
   current observables, 0 after adding observables.
6. **Route at run time, per site**: verbatim/recurring and determined → memory, verify anyway;
   value-inventing → synthesise, never substitute; nothing checkable → the action is the dangerous one,
   so spend there.
7. **Then compose.** The remaining 95% is novel composition of parts that repeat — a small edit basis
   under a verifier (`induced_edit_basis_v1`, `causal_trace_to_skill_compiler_v1`).

## 7. Reproduce

```
python3 canonical/swe_kernel/oracle_density_v1.py --clone \
  --json canonical/verification/ORACLE_DENSITY_20261116_V1.json
python3 -m pytest canonical/tests/test_oracle_density_v1.py -q
```

`--clone` fetches the five corpus repositories once into `/tmp/brain_oracle_density_repos`; after that the
measurement is offline and takes about three seconds. Six tests pin the density, the python-only split,
and the loop arithmetic; the live re-derivation test skips (with a reason) when the clones are absent, so
an offline checkout cannot pass by silence.

## 8. What this does not claim

No capability credit, no benchmark rank, no independent verification. Token naming is a ceiling, not
coverage, and the 0.8021 strength constant was measured on this repository's own mutants — different
repositories, different strength. The corpus is every sixth commit of five Python libraries, and the
per-repository spread (0.344 to 0.815) means the pooled number is a description of a population, not a
prediction for a specific repository. And none of this measures a *manufactured* oracle: it counts the
human-written ones, which is the floor the agent has to beat.

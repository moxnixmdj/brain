# A single trace does not pin the rule — measured, not argued

*`canonical/tools/the_assertion_is_the_demand_v1.py` extended with the live-set and ambiguity counters · 15 tests · receipt `canonical/verification/A_SINGLE_TRACE_DOES_NOT_PIN_THE_RULE_20261120_V1.json` · 30 real commits · zero parameters, zero model calls*

---

## The claim under test

"Instant learning" is two different claims that have been carried as one:

1. **Retention**: an execution that is recorded can be replayed exactly. *True, and solved* — replay held legality in 228 of 228 compositions.
2. **Transfer**: one execution is enough to learn the *rule* that produced it, so the rule can be applied, permanently, in a new environment. *This is the claim that decides capability, and it is false.*

The instrument this round needed already existed: it reads the demanded value out of a failing assertion, records every execution of the changed site inside the recorded frames, and filters the closure by evaluation instead of by oracle questions. Three counters were added to it. They are small. What they return is the answer.

## What the counters say on 30 real commits

| stage | rows |
|---|---|
| structural edit — not a single-expression replacement (censused, not a miss) | 15 |
| the site never ran in the failing test | 1 |
| demand known, no candidate produced it | 13 |
| verified: whole file green, patch = the human's own fix | 1 |

Whole sweep: **93.2 s**, worktrees and verification included, `parameters_stored: 0`.

**The live set.** On every row the instrument offers the same enormous closure — **150,809 to 154,157 candidates** — and asks each one whether it produces the value the failing assertion demanded. The answer is the number that matters:

- on **13 of 15** in-class rows, **zero** candidates produce it;
- on the one row it can verify, **2** do, and both turn the whole file green.

So the failure on this corpus is not that a single trace admits thousands of equally plausible rules. It is that the true rule is usually **not expressible in the closure at all** — which is the vocabulary limit, measured again, and it is the opposite of the failure the identifiability worry predicts. Both failures exist; only one of them is the binding one here.

**The ambiguity of the gate.** On the one row the instrument could verify, the corpus's own suite — whole file, 47 tests — accepts **two syntactically different rules**:

```python
f"Type annotation and type argument cannot both be present for '{name}'."
f"Type annotation and type argument cannot both be present for {name!r}."
```

Both are green. They agree on `name = 'x'`, and the suite never supplies a second name. The only gate the tree permits therefore cannot separate them, and no amount of *storing the trace* will: the trace contains one name.

**The observations are not contrasts.** One row runs the site **109 times** inside a single failing test. That looks like a rich observation set and is not one: the demanded value is due at *one* of those executions, and the other 108 constrain only that the original value be preserved — which the true fix does not do, because it changes the value everywhere. A repetition of one situation is not a variation of it.

## The law this gives

> **One trace teaches a tape. Only a contrast teaches a rule.** A distinction exists when the same action, with exactly one feature changed, flips the outcome. Nothing else does.

Everything the tree has measured for months is a corollary:

- **Retention** (replay 228/228 legal) but **transfer** broken: 53.5 % stale, 31.1 % silently corrupt under change, and independent 2026 work finds the same shape — external memory does not remove continual learning, it relocates it to representation and retrieval, where raw trajectories cause *negative* transfer that is worst on the hardest cases [1](https://pith.science/paper/2604.27003); unfiltered remembering performs **below a no-memory baseline** [2](https://aclanthology.org/2026.acl-long.27/).
- **What does transfer is the form**, never the value. Of fourteen real one-line repairs: attribute of another object 6, method call 3, guard 4, a name already in the frame 2, an f-string 1. A stored trace gives none of these; a stored *form* gives all of them, and the value is re-derived per site for ~10 µs.
- **Even the best weight-free system does not do it in one shot.** JitRL (ICML 2026) needs a memory of `(state, action, return)` triplets, **neighbourhood statistics** and an evaluator for credit assignment [3](https://arxiv.org/abs/2601.18510); the training-free contrastive method distils rules from superior-versus-inferior pairs, not from single runs [4](https://arxiv.org/html/2604.13552).
- **Composition dominates long horizons.** OSWorld 2.0 tasks average 318 tool calls; at 99 % per step the end-to-end rate is ~4 %, at 99.5 % ~20 % [5](https://presenc.ai/research/osworld-computer-use-leaderboard-2026). A perfect action library is still not a solved computer.

## So what is the single bottleneck

Not parameters, not the closure, not the verifier, not the prompt. From first principles the only thing that turns experience into a rule is an **intervention that varies exactly one feature** — and the binding quantity is how fast such pairs can be produced against a resettable, verifiable environment.

This is where 2026 is unambiguous, and it is the same conclusion reached from a different direction: *"the bottleneck is not the learning algorithm but the environment"*, with labs building millions of verifiable, resettable tasks and "replication training" — the same workflow thousands of times **across slightly varied environments** [6](https://arxiv.org/pdf/2610.05923). That is contrast supply, at industrial scale, and it is the one part of the frontier's recipe that our zero-parameter route cannot skip.

## What that means for the plan

- **Coding**: the pair is (failing case, perturbed input) at the same site, verified by the suite. The missing component is a **perturbation harness**, not a bigger grammar — our grammar already contains the fix on the row we solved; the failure was never search, it was that the world only ever showed us one point.
- **Computer use**: the pair is (state, one feature changed), and the reference space is `element × action` read from the accessibility tree. The same instrument, the same arithmetic, the same 0.99^318 wall — which is beaten by checkpoints, not by better clicks.

## What is *not* claimed here

That the 13 `NO_VALUE_MATCHES` rows are impossible — they are a fact about this reader and this closure, reported as such. That 1 of 30 is a ceiling — it is what one trace plus a suite buys, which is exactly the point. That the 15 structural edits are failures — they are outside the instrument's scope and are censused, not counted.

## Reproduction

```
/tmp/venv/bin/python canonical/tools/the_assertion_is_the_demand_v1.py \
  --commits /tmp/corpus/c30.json --receipt canonical/verification/A_SINGLE_TRACE_DOES_NOT_PIN_THE_RULE_20261120_V1.json \
  --survivors-cap 16 --verifications 16 --seconds 180
/tmp/venv/bin/python -m pytest canonical/tests/test_the_assertion_is_the_demand_v1.py -q    # 15 passed
```

Authority NONE. Producer-run. 0 parameters, 0 model calls, 0 network calls at run time.

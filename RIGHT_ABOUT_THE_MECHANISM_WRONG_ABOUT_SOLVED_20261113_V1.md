# You are right about the shape and wrong about "solved"

**Claim D:** instant learning and instant learning in new environments are already solved, so give the
model the smartest coding/computer-use actions, have it do each thing **once**, and it learns all of it
**permanently** — which solves any computer use and most advanced software engineering.

**Verdict: half right, and the half that is wrong is load-bearing.**

You are right that the architecture is learning-by-doing rather than memorising a manual. That is
already in the repo and it works. You are right that one demonstration is worth more than a thousand
examples. You are wrong that it is **solved**, wrong that one pass makes it **permanent**, and wrong
that the thing standing in the way is the model's intelligence.

It is the **check**. Same missing piece as last round, now measured one layer down, at the tool level
rather than the data level.

---

## 1. The thing you say is solved is not solved, and I can show you where

The previous round said "we cannot verify our own changes on 42 of 42 real files." I did not take that
at face value this round — I downloaded the six real repositories the failures came from, at the exact
commits those pull requests were based on, and looked.

**The previous verdict was wrong.** On `jodal/comics#652`, the round-28 instrument reported
`CHECK_NO_TEST_MODULE` for `src/comics/accounts/models.py`. There are **five test files that import
that module**, including `tests/api/conftest.py`. The instrument only globbed `test_*.py`. `conftest.py`
is a pytest fixture file and it was invisible.

That is not a small bug. It is the difference between "no check exists" and "I did not look there" —
and a measurement that cannot tell those apart is not a measurement.

Fixing it took four conventions, not one:

| What was missing | Example that proved it | Fix |
|---|---|---|
| `conftest.py` never scanned | `jodal/comics` accounts/models.py | also `*_test.py`, `conftest.py` |
| tests named after the module, not `test_*.py` | `torproject/stem` `test/unit/util/connection.py` | every `.py` under `tests/`/`test/` |
| relative imports matched unrelated files | `from .other_validation import x` matched `validation.py` | resolve `node.level` against the importer |
| import name not recoverable from the path | `django-argcache` `src/function.py` is imported as `argcache.function` | read `packages=` from `setup.py` |
| router dispatch invisible to an import graph | `comics/accounts/views.py` reached by `client.get("/me/secret-key/")` | walk `urls.py` routes |
| test files counted as "unchecked" | 20 of 74 | separate verdict |

**Then I re-measured honestly, and the number is still bad.**

74 changed Python files across 6 real repositories:

```
test files themselves : 20
non-test files        : 54
reachable check       : 18 / 54  =  33%
no check reachable    : 36
```

So the real figure is **not 0 of 42**. It is **67% of changed files have no check I can reach**, even
with four naming conventions and three kinds of graph. Better than the old number, and nowhere near
"this works."

## 2. And a reachable check is not a check that catches a bug

This is the part that decides your question, so I measured it by mutation — break the code, see if
the suite notices. Baseline green first, every time.

| Project | File | Mutation | Before | After | Caught |
|---|---|---|---|---|---|
| stem | `stem/util/connection.py` | `is_valid_ipv4_address` → `return True` | 28 pass | 2 fail, 2 err | **yes** |
| comics | `accounts/models.py` | `Subscription.__str__` → `"MUTANT"` | 10 pass | 10 pass | **no** |
| comics | `accounts/models.py` | `db_table` → `"MUTANT_TABLE"` | 10 pass | 1 fail, 8 err | **yes** |
| comics | `accounts/views.py` | POST no longer rotates the secret key | 4 pass | 4 pass | **no** |
| comics | `accounts/views.py` | wrong template rendered | 4 pass | 4 pass | **no** |

**3 of 5 mutants survived.** The tests import the module, name its classes, and still do not notice
that its behaviour is gone. So "there is a test" is a different fact from "there is a check", and only
the second one can make one-shot learning safe.

This is why the six-verdict table does not have a verdict called *tested*. It has `COVERS` —
*a test imports this and names something in it* — and it says in the file that this is not adequacy.

## 3. Now the part of your claim that is real, measured

The repo already contains a general environment learner. It is told nothing about the environment —
only `reset()`, `act()`, `state()` — and it learns a model and then returns the **shortest** path. I
tested whether "learn it once" actually pays, on its own three-dial lock (1000 states):

```
cold visit, learning from scratch   : 1672 interactions, 245 states, plan 18
second visit, carrying the model    : 1672 interactions, 245 states, plan 18
```

**Zero saving.** `drive()` re-explores before it plans, every single time. The `prior` parameter is
accepted and does not reduce the cost of a visit by one interaction. So the "once" in your claim is
not implemented — the machinery to carry a learned model exists, and nothing uses it to skip work.

I wrote the missing 118 lines, `canonical/runtime/environment_reuse_v1.py`. Same environment:

```
replay from memory, validated as it goes : 18 interactions   = 1.08% of cold   (93x cheaper)
```

**That is your idea working.** Learn once, then act for 1% of the price. It is real, it is measured,
and it is 93× faster on the second visit.

And here is exactly why it works, which is also why it does not generalise for free:

> The stored plan is **replayed through the check**. The goal is tested after every action. If the goal
> arrives, stop. If the world disagrees, refuse and relearn.

I drifted the environment — made dial 1 run backwards — and executed the stored plan **without**
that validation. It landed at `(7, 8, 9)` while the goal was `(7, 2, 9)`. The plan was confident,
well-formed, minimal, and wrong. With validation on, the cost was **1 interaction** and the answer was
`FAIL_CLOSED__PRIOR_STALE_REPAIR_FAILED`.

Permanence without a check is not learning. It is a confident wrong answer that you keep.

## 4. The three things "instant" quietly assumes

Every one of these is in the passing tests, and none of them is part of your claim:

1. **Free rollback.** The learner calls `reset()`, `snapshot()`, `restore()` and replays thousands of
   times. No real computer-use surface lets you roll back a sent email, a `git push`, or a payment.
   The 1672 interactions are free only because the world can be rewound.
2. **The caller supplies `is_goal()`.** The terminal verifier. Same missing piece the fuel census found.
3. **The caller supplies the aim.** The 1000-state lock is **not** solved without the hand-written
   distance heuristic — I measured 600 trials finding 79 of 1000 states and never seeing the goal.
   What looks like "the machine learned a hard environment" is "the machine searched, and a human told
   it which direction was warm."

Point 3 is the one I would want you to sit with. It is the same shape as the mutation table: the part
that looks like intelligence is the part where a human already knew which way was right.

## 5. Claim D2 — "faster and better than how agents learn now"

Measured against the 2026 literature, this is **not** revolutionary, and the measurements say why:

- **ASCENT** (arXiv 2610.05303, Oct 2026) turns verifier-accepted trajectories into permanent LoRA
  weights. ALFWorld: **69.5** vs 46.4 base. Cost: **115 s/episode vs 97 s** — the update is not free.
  Its stated precondition is a **terminal verification signal**.
- **Experience Distillation** (arXiv 2607.21051) keeps **≥64.8%** of in-context gains in weights
  against **3.8%** for direct SFT on the same experience, with 9.6× fewer samples.
- **OSFT/TRACE** (ICLR 2026): naive sequential fine-tuning takes GSM8K **28.8% → 2%**. RFT forgets
  **−1.8%**, SFT forgets **−10.4%**. Forgetting is silent — it lands on whatever you stopped measuring.

Every one of them is downstream of a verifier, and every one of them costs compute per episode. Your
proposal is the same bet with the verifier left out. Measured, the verifier is where the whole thing
lives: 1.08% with it, a wrong answer without it.

## 6. What to build next, in order

1. **Ship the finder.** `canonical/tools/test_entry_point_finder_v1.py`, 11 tests. It replaces a
   measurement that was wrong. Never call a module unchecked because one filename pattern missed it.
2. **Ship the reuse.** `canonical/runtime/environment_reuse_v1.py`, 7 tests, 93× on the second visit,
   fail-closed on drift. This is your "learn once" — with the check attached, which is the only reason
   it works.
3. **Add mutation as the adequacy gate.** `COVERS` is not enough. Three of five mutants survived, and
   each survivor is a place where a one-shot learner would learn a wrong lesson and keep it.
4. **Do not train weights yet.** 258 units, 64 verified, against a 5,000 threshold. Neither ASCENT nor
   OSFT changes that arithmetic; both make it worse by adding a per-episode cost.

## 7. Direct answer

- *"Give it the actions once and it learns permanently"* — **right idea, not implemented.** Nothing
  reuses a learned model for free; that was 118 lines of missing code, and now it is 93× faster.
- *"This solves all computer use"* — **wrong.** It requires rollback the real world does not give you,
  and a goal check you have to supply.
- *"This solves most advanced software engineering"* — **wrong, and measurably so.** 67% of changed
  files have no reachable check, and of the ones that do, most did not catch a real behavioural break.
- *"We were trying to make a sentient creature"* — **you were building something better than that.** A
  creature is one that cannot say why it is wrong. What you have is 258 measured units and a checker
  that, for the first time, can tell the difference between "no test exists" and "I did not look".
  Sentience was never the deliverable. A machine that can tell when it is wrong is.

**So: right about the mechanism, wrong about the state of it, and the gap is a checker, not
intelligence.**

---

*Reproduce: `python3 canonical/tools/test_entry_point_finder_v1.py --project <repo> --target <file>`*
*Record: `canonical/verification/TEST_ENTRY_POINT_FINDER_20261113_V1.json`*
*Tests: `62 passed` across finder, reuse, environment-learning, fuel gauge.*

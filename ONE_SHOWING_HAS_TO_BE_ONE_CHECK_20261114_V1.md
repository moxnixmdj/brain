# You are right about the mechanism and wrong about "therefore everything" — and the gap is now a number

**14 November 2026.** Branch `arena/98e3c624-brain`, base `fee45dc4`.
Authority **NONE**. Producer-run sandbox measurement, `$0`, zero model calls, no capability
registered, no family flipped, `truth.achieved` stays `false`. Nothing here is an independent
verification, and none of it is a claim about sentience.

You asked three things: *is "show it once and it is learned permanently, everywhere" true — and if
so does that solve any computer use; what is real and what is not; and what are the smartest things
to do.* This answers them in that order, by measurement, and it adds the one organ the previous
thirty rounds kept assuming instead of measuring.

---

## 0. The one-sentence answer

**A demonstration is a point, a check is a quantifier — and on real repositories the check is blind
to a quarter of the places a lesson can land.** Measured here on three independent repositories:
12 of 50 sites had no test that could notice the behaviour changing. At those sites every
"REPAIRED", "PRESERVED" and "verified" verdict this repository produces is the check's silence being
read as its agreement. That is the limiting factor, it is measurable, and it costs minutes.

---

## 1. Your claim, decomposed and measured

`canonical/tools/one_showing_one_check_table_20261114_v1.py` runs the tree's own machinery against
its own shipped demonstration (`def classify(x): return x <= 100` → `< 100`) and answers each clause:

| clause | measured | evidence |
|---|---|---|
| 1. A change shown once is kept | **TRUE** | `crystallized=True`, one row in a real store |
| 2. It transfers to a function it was never shown | **TRUE** | the rule rewrote `at_cap(n): return n <= 50` into exactly `n < 50` |
| 3. **The check can tell a right change from a wrong one there** | **FALSE** | 1 of 2 sites licensed; the taught boundary is not among them; perturbing `<=`→`<` changed **no** passing test |
| 4. Permanence is safe: a wrong version is refused | **TRUE** | admission **REJECT**s it, 0 rows written |
| 5. The same trick covers anything on a computer | **NOT MEASURED** | this tree has no computer-use surface that executes real applications |

So: **you are right about 1, 2 and 4.** Learn once, keep it, apply it to a new function of the same
shape, and refuse a harmful version of it — all of that works, here, today.

**You are wrong about 3, and clause 3 is what makes the rest permanent.** The lesson about a
boundary was admitted and would have been re-applied forever, and the project's own tests could not
have refused it, because they called the function at 10 and at 100 and never at the boundary. That
is not a hypothetical: it is the fixture, and it is the common shape. *Permanence multiplies
whatever the evidence was worth* — and here the evidence was a check that could not disagree.

---

## 2. The thing nobody had measured, now measured on real code

Every previous round ended with "the check is the bottleneck". The check was then treated as given.
It is not given. `canonical/swe_kernel/oracle_licence_v1.py` answers one question per site:
**perturb this behaviour — does the check notice?**

Method, and why each choice is forced:

* **Mutants are byte splices, verified against the AST.** Five operator families (`<`↔`<=`↔`>`, `+`/`-`,
  `and`/`or`, `return X` → `return None`). A splice is discarded unless the file still parses **and**
  the parsed program changed. So docstrings, comments and formatting are never touched, and a
  "mutation" that is the same program is not run at all.
* **Caught means a test that passed before now fails.** This is SWE-bench's fail-to-pass rule at
  mutant granularity. It is what makes a repository with pre-existing failures measurable at all —
  a red test cannot make anything look caught, so nothing has to be excluded by hand.
* **A load probe runs first.** Write an unparseable version of the file; if the check still passes,
  it never imports the file and *nothing is measured* — `REFUSED_CHECK_DOES_NOT_LOAD_THE_FILE`.
  This fired on `pypa/packaging`: without it, the first run reported "0 of 8 sites licensed — the
  tests are blind", when the truth was "the harness was importing the installed copy". That is the
  same class of error as the round-13 finder bug (`CHECK_NO_TEST_MODULE` because it only globbed
  `test_*.py`), one layer down, found the same way — by running it.
* **Restore is proved, not promised.** Original bytes are written back in a `finally` and compared
  by hash before the next mutant. A runner that leaves a mutant behind turns every later measurement
  into fiction.
* **A licence is bought once.** Content-addressed on file hash + check command + budget. The same
  bytes cost nothing the second time; a changed file is measured again.

### The measurement

Three repositories, fetched from `codeload.github.com`: `torproject/stem`,
`more-itertools/more-itertools`, `pypa/packaging`. Five files, 50 sites, 52 perturbations,
441 machine-seconds. Record: `canonical/verification/ORACLE_LICENCE_CROSS_PROJECT_20261114_V1.json`.

| file | passing tests (the quantifier) | sites licensed | perturbations caught |
|---|---:|---:|---:|
| `stem/util/tor_tools.py` | 6 | **5 / 10** | 5 / 10 |
| `stem/util/term.py` | 2 | **7 / 10** | 7 / 10 |
| `stem/util/connection.py` | 28 | **8 / 10** | 9 / 12 |
| `src/packaging/utils.py` | 79 | **9 / 10** | 9 / 10 |
| `more_itertools/recipes.py` | 145 | **9 / 10** | 9 / 10 |
| **total** | | **38 / 50 = 76%** | **39 / 52 = 75%** |

**Not one file was fully licensed.** Between 1 and 5 sites per file were blind. 24% of the places a
one-shot lesson could land are places where the check cannot tell a right change from a wrong one.

Two honest qualifications, because the number is easy to over-read in both directions:

* **Most of the survivors are one operator's weakness.** 9 of the 12 refused sites are
  `return X → return None` where `X` is `False`: `None` is still falsy, so the perturbation is
  (nearly) equivalent. That is the known-cost half of mutation testing, it is labelled per site with
  the survivor named, and it means the true behavioural blindness is somewhat below 24%. It is *not*
  zero: `stem/util/connection.py` had a real `<=`→`<` guard belong to no passing test.
* **This is not a benchmark.** Three repositories, five files, chosen because their own suites run
  here, not sampled. It is a measurement with a denominator, not an estimate of prevalence.

### The cost, which decides the design

Per mutant: **0.45 s** for a 2-test suite, **25 s** for a 145-test suite. The price of a licence is
`mutants × the cost of the check`, so the licence is bounded (sites in line order, deterministic, no
sampling), cached, and reusable. Buying it every time would make the honest thing the expensive
thing, and the expensive thing is the one that gets skipped.

### What shipped

* `oracle_licence_v1` — per-site licence: `ALL_LICENSED` / `PARTIAL` / `NONE_LICENSED`, and refusals
  that are **not zeros** (`REFUSED_CHECK_DOES_NOT_LOAD_THE_FILE`, `REFUSED_BASELINE_RED`,
  `REFUSED_FLAKY_BASELINE`, `REFUSED_NO_MUTANTS`).
* Wired at the chokepoint every learn path uses: `crystallize_code_fix(..., oracle_licence=...)`
  **refuses** a lesson at a site the licence did not license, and records `UNLICENSED` when a caller
  supplies none — so the unlicensed case is counted instead of assumed.
* `LicenceCache`, `licence_for_codebase` / `project_permission` for project scope, and a sentence
  (`render_licence`) that names the blind line rather than printing a score.
* 48 new tests, all executing, most needing no check at all (stdlib `unittest` fixtures; the whole
  file runs in ~5 s). Plus the measurement re-run tool.

---

## 3. Then there is the layer underneath, and it is worse than "not solved"

The repository already contains the refutation of its own older claims, and I am not going to
re-litigate them. What matters for *your* plan is the shape they all have, because it says what the
next piece of work must be:

* `lesson_admission_gate_v1` (13 Nov) — one demonstration produced a rule that **repaired one unseen
  program and broke another that was already right**. The gate now refuses that. Good.
* `weight_update_admission_v1` (13 Nov) — **32 of 32** weight updates certified themselves
  successful; the layer ended up agreeing with the tree's own parser on **5 of 32** and **broke 3
  predictions that had been right**. Gated, it kept 1 of 32.
* `test_entry_point_finder_v1` (13 Nov) — **3 of 5 mutants survived** on two real projects. A test
  that imports a module and names its classes, and still cannot notice its behaviour is gone.
* `environment_reuse_v1` — replaying a learned plan costs **1.08%** of the cold cost, and it works
  **only because the plan is replayed through the goal check**. Executed blind on a drifted world,
  it landed at `(7,8,9)` against a goal of `(7,2,9)` — confident, minimal, and wrong.

Four different organs, one sentence: **permanence without a check is a confident wrong answer that
you keep.** Today's measurement puts a number on the check itself for the first time.

---

## 4. Your model-building question, answered honestly

You want weights built from scratch, every bit calculated, *the best part is no part*, and an
external instant-knowledge source instead of a knowledge house in the parameters. Two things are
true and they point in opposite directions, so keep them apart:

1. **"The best part is no part" is the correct law for this system, and it is already paying.**
   This round added no model, no embedding, no training run — 800 lines of Python that measures a
   property of an *existing* check. It changed what the system is allowed to believe about its own
   lessons. That is the cheapest capability this repository has bought in weeks.
2. **"Build our own weights, therefore skip the check" does not follow, and the 2026 literature says
   so from every direction.** `aTTT` (arXiv 2607.03441) delivered the same summary as a weight update
   and as context: 54.3% vs 49.3%, with the in-context arm *below* the no-adaptation baseline —
   weights can carry signal a prompt cannot. But the gains "concentrate where models already have
   task competence", i.e. weights **preserve** competence. `Continual-ARC` (arXiv 2611.14505):
   "no harness-based method gains on unseen tasks, whereas weight-based learning shows substantial
   gains" — the strongest evidence for your thesis — and the same paper reports that policy gradient
   and self-distillation **both failed to learn reliably**; what worked was DAgger, i.e. teacher
   correction *on the student's own states*. Every path there runs through a verifier.

A constructed model is not exempt from clause 3. A check is what tells a self-built model which of
its own outputs were right, and it is the only thing that can. Skipping it does not make the model
freer; it makes the training signal the model's own opinion, which is exactly the `32 of 32
self-certified` result above, scaled up.

So: build the weights, keep the law, and keep the licence. In that order the weights are trained on
admitted, deduplicated, contrastive traces whose *checks were shown able to fail* — and not
otherwise.

---

## 5. What is real, what is not, in one table

| claim | verdict | the number behind it |
|---|---|---|
| One showing is kept permanently | **TRUE** | 1 row, real store; 384/726 developer changes at precision 1.000 on 12 merged PRs (prior round) |
| It transfers to an unseen place | **TRUE, same shape** | rewrote `at_cap(n): n <= 50` correctly; refused on 4 of 4 *different* shapes (prior round) |
| One showing is enough to learn anything | **FALSE** | one demonstration eliminated 1 of 34 candidate repairs; a test eliminated 28 |
| The check can see the change it blesses | **FALSE on this fixture and 24% of real sites** | 0 of 1 at the taught boundary; 38 of 50 sites licensed over 3 repos |
| Permanence is safe | **TRUE where the licence holds, FALSE where it does not** | admission REJECTs the harmful version; the licence is what says which regime you are in |
| It works in new arbitrary environments | **FALSE as stated** | refused on all four new shapes; 67% of changed files have no reachable check (prior round) |
| It covers anything on a computer | **NOT MEASURED, not close** | 0 of 5 in-tree surfaces execute a real application; frontier OSWorld 2.x binary completion ≈ 31% |
| The model needs to be sentient for this | **Unmeasurable, and not the blocker** | the blocker is a check that can fail, which is engineering |

---

## 6. The smartest next actions, in order, and the ones killed on the way

**Do these, in this order.** Each is measurable with what is already here.

1. **Make the check reach the file, and say so.** 67% of real changed files had no reachable check
   (prior round). The finder exists; it is not wired into the learn path. Until it is, a licence
   cannot be bought for two thirds of the code a lesson would be applied to.
2. **Fix the operator that manufactures refusals.** `return X → return None` is 9 of the 12 blind
   sites here. Replace it with value-preserving-class substitutions (`return True → False`, numeric
   bumps) so the licence measures behaviour rather than falsiness. Cheap, and it makes every
   subsequent number smaller and truer.
3. **Hold the correlation that this round only noticed.** Site-licence fraction rose monotonically
   with the number of passing tests across all five files (ρ = 1.0 at n = 5, which is worth nothing
   yet). Re-run on 50 files. If it holds, "stand up a check" and "make the check able to see the
   change" are the *same* work — and the repository's #1 bottleneck gets a number that can be
   pushed.
4. **Then the second showing, automatically.** The organ already transfers when given two
   demonstrations that differ where the rule must vary. Choosing the second showing by *which place
   it varies* is a small change to working code, and the prior round measured it moving 0.529 →
   0.891 of the developers' work at 0 wrong.
5. **Then a confined computer-use surface, for clause 5.** Observation, rollback, a success
   predicate — and the same licence question asked of it: *can the success predicate fail?* Not a
   stub. A stub would make the row say TRUE and mean nothing.

**Killed before implementation, with the reason:**

* *"Give it every advanced action once and it learns everything."* Killed by clause 3 plus the prior
  0.529/0.891 figures: the reach comes from a second differing showing and a check, not from
  repetition.
* *"Build the weights first and the check will follow."* Killed by `32 of 32 self-certified`: a
  self-built model with no verifier learns its own errors at scale.
* *"Score the repository with one big mutation score."* Killed on cost: 25 s per mutant on a real
  suite; a codebase-wide score is hours and answers a question nobody asked. Per-site, bounded,
  cached is the version that gets used.
* *"A model judging correctness."* Forbidden by the standing constraint, and it is not independent —
  it is the proposer grading itself one layer up.
* *"Sample the sites randomly to make it cheaper."* Killed because a licence that changes between
  two runs of an unchanged file cannot be compared with itself, and comparison over time is most of
  its use. Sites are taken in line order.
* *"Treat a refusal as a zero score."* Killed in the design: every refusal returns
  `fraction_licensed = None`, because a suite that is already red or a file that is never imported
  is *no evidence*, and no evidence must never read as "fully licensed".

---

## 7. What this does not claim

This is not a benchmark, not an independent verification, and not a capability. It does not say a
licensed site is correct — only that *these* perturbations were seen; mutation adequacy is evidence,
not theorem. It does not say a refused site is a defect in anybody's tests. The cross-project corpus
is three repositories chosen for runnable suites. The ρ = 1.0 in §6(3) is five points and means
nothing yet, which is why the next step is to gather fifty. `truth.achieved` is untouched, no family
is flipped, spend is `$0`, and no model was called.

Reproduce the whole thing:

```
python3 canonical/tools/one_showing_one_check_table_20261114_v1.py
python3 -m pytest -q canonical/tests/test_oracle_licence_v1.py \
    canonical/tests/test_lesson_admission_requires_a_licensed_check_v1.py \
    canonical/tests/test_one_showing_one_check_table_v1.py
python3 canonical/tools/oracle_licence_measure_v1.py --out /tmp/licence_rerun.json   # needs network
```

One sentence to keep: **the lesson was right, the rule transferred, admission refused the harmful
version — and the check still could not have caught it. That is the wall, and it is built out of
missing tests, not missing intelligence.**

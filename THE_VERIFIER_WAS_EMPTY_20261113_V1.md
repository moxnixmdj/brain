# No — and the reason is not the one you think. Our verifier was running zero tests and reporting PASS.

**2026-11-13.** Base `b8c42ebce3`. Branch `arena/0de25c4e-brain`.
Authority **NONE**. Producer-run, one machine, `$0`, zero model calls. No capability registered,
no family flipped, `truth.achieved` stays `false`.

You asked: *we solved instant learning and instant learning in new environments perfectly — doesn't
that mean all computer use, including the most advanced software engineering, is solved? Show the
agent the smartest action once and it learns permanently.* And you offered three options:
token-space only, add weight-space, or both.

I went looking for the limiting factor before choosing an option. **I found something worse than a
missing capability: a check that could not fail.** That changes which option is smartest, so this
round fixes it and measures it rather than arguing about it.

---

## 1. Direct answer to the claim

| your claim | verdict | why |
|---|---|---|
| One showing teaches a change permanently | **Partly true, narrowly** | Prior round measured 384/726 changes right, **0 wrong**, on 12 real PRs — *inside one project* |
| One showing works in a new arbitrary environment | **False** | The same lesson shown once was **refused on all four** new shapes tried |
| Therefore all computer use is solved | **False** | The premise fails, and so does the conclusion independently — see §2 and §3 |
| Therefore advanced software engineering is solved | **False, and not close** | Frontier is ~44–49% binary on OSWorld 2.1 and ~66% on Terminal-Bench 4.1 |
| Weight-space learning is the missing piece | **Real, but not first** | It is a real technique; it is not our binding constraint today — §4 |
| Option 3 (both) is the right target | **Yes, eventually — in a specific order** | §6 |

### The arithmetic that settles "show it once"

The repo's own probe, run this round, using the *same* candidate generator the repair loop searches
with:

```
candidate programs generated from the shipped mutation families    34
consistent with ONE demonstration  grade(95) == 'A'                33
consistent with the three assertions                                6
consistent with the demonstration and WRONG on the suite           27
```

**One demonstration eliminated 1 of 34 candidates. A test eliminated 28.** Twenty-seven programs
agree perfectly with your one showing and are wrong. This is not a philosophical objection; it is
a count. A demonstration is a *point*. A test is a *quantifier*. No amount of permanence granted to
a point turns it into a quantifier — you simply keep the wrong program forever instead of for a
while.

That is why "learn it once and keep it permanently" is not automatically good news. **Permanence
multiplies whatever the evidence was worth.** If the evidence underdetermines the answer,
permanence makes the error permanent too.

---

## 2. What I found instead of a learning problem

Every method you cited learns from a **verified** trajectory. ASCENT skips the weight update when
verification fails. Experience Distillation distils from accepted trajectories. So I asked the
question that comes before any optimizer purchase: *when our check says PASS, did it run anything?*

The shipped check stood up a project's tests with `python -m unittest <module>` and treated
`returncode == 0` as "the tests pass."

`unittest` **cannot see pytest-style tests.** On a module with plain `def test_*()` functions and no
`TestCase`, it collects nothing, prints `Ran 0 tests ... OK`, and exits **0**.

Measured on this repository at the base commit:

| | files |
|---|---|
| test files scanned (tracked at base) | **2,592** |
| collectable by `unittest` | 1,596 |
| **pytest-style — `unittest` runs 0 tests and exits 0** | **943 (36.38%)** |
| neither collector | 53 |

Two live witnesses, run both ways:

```
canonical/runtime/test_requirement_graph_kernel.py
    unittest: Ran 0 tests ... OK  (exit 0)      pytest: 10 passed
canonical/runtime/test_prequalification_stage_a_reducer.py
    unittest: Ran 0 tests ... OK  (exit 0)      pytest:  4 passed
```

And the counterfactual, on a constructed project with two real assertions:

| | original file | **broken file** (`return None`) |
|---|---|---|
| legacy check | accepts | **ACCEPTS** |
| repaired check | accepts | **refuses** |

**A check that accepts a deliberately broken edit is not a weak oracle. It is a false one.** A
missing check is honest — it says *unknown* and the caller refuses. This one said *verified* about
an edit nobody tested.

### Why this outranks every learning idea on the table

- **ASCENT** skips the update when verification fails. A verifier that cannot fail trains on every
  trajectory, wrong ones included, **permanently**. Your permanence requirement makes this worse,
  not better.
- **Experience Distillation** is only as good as its acceptance bit. Ours was, in the affected
  regime, a constant `True`.
- **Token-space reuse has the identical dependency.** The repo's own probe
  `a_failure_is_a_context_not_a_ban` shows a boundary requires a *real* contrasting failure. A
  vacuous pass supplies none, so the lesson generalises past the situation that made it true.

This is not test hygiene. It is the admission gate on the learning signal, and **both of your
options sit on top of it.** Terminal-Bench 4.1 shipped on 2026-11-09 regrading *saved trials* with
hardened verifiers — the frontier moved the checker, not the tasks. The field is learning the same
lesson from the other direction.

### What shipped

`canonical/swe_kernel/check_collection_admission_v1.py` — runs the check and returns **how many
tests actually executed**. Zero is never a pass. When `unittest` collects nothing, the pytest
collector is tried, so those 943 files become real checks instead of false ones. When neither
collector can run, the reason is reported and the caller refuses.

Wired into both places that consumed the old exit code (`Check._runs` and `Check.accepts`) — not
left as an orphan organ, which this repo has been burned by before.

Three bugs of my own that the tests caught before shipping, recorded because they are instructive:
bytes-vs-str comparisons; counting a pytest **collection error** as a test that ran; and trusting
`unittest`'s `Ran 1 test ... FAILED (errors=1)`, where that "1" is a synthetic `_FailedTest`
placeholder for an import failure, not a test of your code. All three would have blamed the edit
for the machine.

**Evidence:** 24 new tests pass; 74 compatibility tests pass; the two existing consumers
(`test_the_check_is_the_difference_v1` 15, `test_across_environments_v1` 17) pass. The load-bearing
test refuses the broken edit that the legacy path accepted, and a separate test *pins the legacy
behaviour* so the defect cannot be quietly redefined away.

---

## 3. Is our accumulated experience even a training set?

Your Option 2 assumes we have experience worth distilling into weights. I audited the five durable
stores against the five properties the published methods actually require. The screen ships a
positive control and five single-requirement ablations, so it can fail — a gate that rejects
everything would pass every "does it catch bad rows" test while measuring nothing.

| store | rows | ready | outcome classes | duplicate rows |
|---|---|---|---|---|
| `GENERALIZATION_EXPERIENCES_V1` | 24 | **0** | success only | 14 |
| `COMPILED_WORKFLOWS_BUNDLE_V1` | 11 | **0** | none recorded | 0 |
| `ASSOCIATIVE_MEMORY_V1` | 12 | **0** | none recorded | 1 |
| `TRANSFER_LEARNING_EPISODES_V1` | 1 | **0** | success only | 0 |
| `TAUGHT_WORD_LESSONS_V1` | 23 | **0** | none recorded | 0 |
| **total** | **71** | **0** | **0 stores hold a failure** | |

The generalization store holds **24 records, 8 distinct tasks, zero failures** — and the reason is
structural, not accidental: `store_experience` is called *only after* postconditions pass. Every
failure path returns before reaching it. **The corpus cannot contain a negative example.** A store
that has never seen a failure cannot represent where a lesson stops applying.

The trajectories are also prose (`"parse file with ast.parse()"`), not executed actions with
observations. Experience Distillation queries a teacher at *recorded history prefixes*; there are
no recorded prefixes here to query.

So Option 2 is not blocked on a GPU. **It is blocked on having a corpus.** Fine-tuning on these 71
rows would distil 8 hand-written tasks and no boundaries. The published number for naive SFT on
collected experience is **3.8% of the in-context gain**, versus ≥64.8% for the distillation
objective — and that is with a *good* corpus.

---

## 4. Your "Brutal Truth" analysis, adjudicated

You wrote that our semantic generalization is a limited lookup system, and that real generalization
needs weight training, conceptual understanding, cross-domain transfer, and reasoning about *why*.

**Mostly correct, with one important correction.** The diagnosis of the current engine is right —
the prior round measured that its "novel vocabulary" is a hand-written synonym table
(`enumerate → count`), and its executed answer does not come from the memory.

The correction: **weight training is not the top missing item.** All three papers you quoted are
real, and I verified them:

- **ASCENT** (arXiv:2610.05303) — real, and it reports that naive imitation or single-attempt policy
  gradient on the model's own tokens **destabilizes the policy**. Its fix needs a frozen teacher
  emitting **full next-token distributions**, which means **open weights only**. It cannot be
  applied to a closed API model at all. Gains are on ALFWorld/WebShop/AppWorld, not SWE.
- **Experience Distillation** (arXiv:2607.21051) — real; ≥9.6× fewer environment samples than RL,
  but direct SFT on the same experience recovers only **3.8%**.
- **Letta Memory Models** — real; token-space memory plus memory-native meta-RL.

And the honest counterweight: **aTTT** (arXiv:2607.03441) reports its test-time updates
*"mainly preserve existing competence rather than teaching new abilities."*

Weight-space learning is real and worth doing. It is not a switch that converts "limited lookup"
into "understanding," and every implementation of it presumes the verified corpus we do not yet
have. This sandbox has no GPU, no torch/jax/numpy, and ~3.8 GiB RAM, so I cannot measure a
weight-space claim here — **I will not claim one I cannot measure.**

---

## 5. The three things actually blocking "any computer use"

1. **Verification coverage.** On the 12 real PRs, **0 of 42 changed files were verifiable** — 6 tasks
   had no test module importing the changed file, 6 needed an uninstalled dependency. This round
   removes a fourth failure mode hiding inside that number: checks that *appeared* available and
   were empty. Standing up a real check remains the largest single lever.
2. **One demonstration underdetermines the program.** 33 of 34 candidates fit one showing; 27 are
   wrong. The fix is a second *differing* showing or a real test — more repetition of the same
   showing buys nothing (measured).
3. **The corpus has no failures and no provenance.** §3. Both learning layers need this.

Notice that none of the three is "the model isn't smart enough." That is the useful result.

---

## 6. The smartest path, in order

**Do now (this round):** make a check prove it ran something. *Shipped.* It is a prerequisite for
both options, it is cheap, and it was silently poisoning the signal.

**Next, in this order:**

1. **Stand up checks where none exist** — resolve declared dependencies (6/12 tasks) and find the
   test entry point that imports the changed file, including *transitive* imports (6/12). The
   current finder only sees direct imports. This converts an unknown share of the 0.529 into
   *verified* work, and every later number depends on it.
2. **Give the store a failure channel with provenance.** One field, measurable consequence: does a
   lesson whose check failed stop being offered? Required by ASCENT, EPD, and token-space reuse
   alike.
3. **Make the second showing automatic** — choose it by *which place it varies*. The organ already
   transfers when given two differing showings; today a human picks the second.
4. **Then weight-space, and only on a corpus that passes the readiness screen** — open weights,
   distillation objective (not naive SFT), verified-and-filtered trajectories, held-out evaluation.
   Not before step 1, because without a real verifier you would be permanently training on noise.

**Killed before implementation, with reasons:**

- *"Fine-tune on our traces now."* 71 rows, 8 distinct tasks, 0 failures, prose trajectories. Would
  produce a confident model of almost nothing. Also unmeasurable here.
- *"ASCENT on our current model."* Requires full next-token distributions → open weights. Not
  available; claiming it would be fabrication.
- *"More demonstrations of the same thing."* Measured: does not widen anything.
- *"A wider/more general rule."* Measured worse: precision 0.455, **42 wrong changes**.
- *"Semantic similarity/embeddings will close it."* Already shipped as #6808; its answer does not
  come from the memory.
- *"Build the weight-space trainer first because it's the deepest fix."* It is the deepest-*sounding*
  fix. The measured binding constraint is upstream of it.

---

## 7. The creature question

You said the deeper goal was to make the model a sentient creature. I won't claim sentience; this
repo cannot measure it and I will not pretend otherwise.

But there is a real, measurable version of the ambition, and this round sharpened it. A creature
whose senses report success no matter what happened is not a creature — it is a loop with a
disconnected sensor. **943 of our test files were exactly that: a sensor wired to `True`.** Before
wanting the system to understand *why*, it has to be able to notice *that it was wrong*. This round
gave back a piece of that ability, and measured that it now refuses an edit it used to wave through.

That is a smaller claim than sentience and a real one, and it is on the path.

---

## 8. What this does not claim

Not a benchmark. The 36.38% census is a *static shape* count over this repo's own test files; the
two live witnesses and the constructed counterfactual are what establish the behaviour, and the
counterfactual project is constructed and labelled so. Passing the readiness screen would be
necessary, not sufficient, for weight training to work. The 0/42 verification figure is from the
prior round's 12-task corpus of mechanical migrations — the regime one-shot learning is *best* at,
so it is a favourable sample, not a representative one. No capability registered, no family flipped,
no terminal credit, `$0`, zero model calls.

Reproduce:

```
python3 canonical/tools/experience_corpus_training_readiness_v1.py
python3 -m pytest canonical/tests/test_a_check_that_ran_nothing_is_not_a_pass_v1.py \
                  canonical/tests/test_experience_corpus_training_readiness_v1.py -q
python3 one_example_is_a_point_a_test_is_a_quantifier_probe_20261112.py
```

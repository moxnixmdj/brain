# One example is a point; a test is a quantifier

**2026-11-12.** Base `f8e6d2ea`. Branch `arena/29f1e2b9-brain`. Round 10.

The question is why an agent cannot be shown an action once and keep it. Round 8 answered it for
*bindings*: one lesson teaches a word, and that works. This round answers it for *programs*, by
counting.

The space is the repository's own: `_candidate_specs` and `_CandidateRenderer` from
`python_test_guided_patch_search_v1.py`, the pair `python.patch.search.test_guided.ast.v1` searches
with. A wrong `grade()` is enumerated into every single-mutation candidate it can produce, and each
candidate is asked two questions:

```
candidate programs generated from the shipped mutation families   34
consistent with ONE demonstration  grade(95) == 'A'              33
consistent with the three assertions                              6
...of which also match the demonstration                          6
consistent with the demonstration and WRONG on the suite         27
pruned by one demonstration                                       1
pruned by the suite                                              28
```

**One demonstration eliminated exactly one program out of thirty-four.** Three assertions eliminated
twenty-eight. The demonstration is not a weaker version of the test; it is a different kind of
object.

Authority **NONE**. In-process, no subprocess, no writes, nothing in the tree touched, $0, zero model
dependency.

---

## 1. Why the ratio is not an accident of this fixture

A demonstration says: *at this input, this output.* One point. A test says: *for every input in this
domain, this relation holds.* A quantifier. They differ in kind, so they differ in what they can
exclude.

The thirty-three survivors are not exotic. They are `90 -> 91`, `80 -> 79`, `if not …`,
`if score is None: …`, and one comparison swapped in the wrong branch — the ordinary mistakes a
search makes. Every one of them agrees with `grade(95) == "A"` and disagrees with the domain. The
suite keeps six, all of which also satisfy the demonstration: **the quantifier subsumes the point, and
never the other way round.**

Note also what the six contain — `score >= 90`, `score > 89.955`, `score > 89.9955`. The suite does
not identify one program either; it identifies a small family. That is why the repair loop replays
its winner twice before keeping it, and why "acceptable" is a property of a predicate rather than of
a program.

## 2. Why the repair loop already knows this

`python.patch.search.test_guided.ast.v1` **refuses to run** when the baseline already passes
(`BASELINE_ALREADY_PASSES`). It requires a failing test as its oracle. That is not an implementation
detail; it is the design admitting the exact thing this probe measures: a search that is not
constrained by a domain statement cannot distinguish a fix from a coincidence.

Which means the proposal "let it experience the action once and keep it" would rebuild the defect
rounds 5–7 spent themselves removing. An acceptance test that admits 33 of 34 programs is a rubber
stamp with better manners. The gate would go green, the wrong program would be kept, and — this is
the part that costs months — it would be **kept permanently**, because permanence is exactly what the
gate was asked to certify.

## 3. The two laws, together

From round 9:

> **Reach = (operators you have) × (bindings you have learned).** Experience buys bindings; code buys
> operators.

From this round:

> **Identification = (operator space) vs (constraints).** A demonstration is the weakest constraint —
> one point. A test is stronger — a domain. An independent recomputation with a refusal is strongest,
> because it cannot be satisfied by a wrong answer at all.

Put together, they say precisely why the owner's instinct is right and his plan is not:

**One experience is enough to *bind* an operator, and never enough to *identify* one.** The taught-
words learner works from one lesson exactly because its operator space is fourteen parts, written by
hand, and the lesson only has to choose among them. The repair loop needs a test for the same reason
mirror-imaged: its operator space is unbounded, so nothing short of a domain statement constrains it.

## 4. What to do, unchanged and now priced

1. **Write parts, not experiences.** Each new action: an enumerable form, an independent
   recomputation, a refusal that names the domain. Sixteen lines bought `median`; that is the unit of
   progress.
2. **Bind with one demonstration once the part exists.** That is the half of the thesis that is true,
   and it is cheap.
3. **Never let a demonstration be the acceptance test.** If a gate can be satisfied by one point, it
   will be. Rounds 5–7 were the cost of learning this the hard way; this probe is the price list.
4. **Close the debt**: `python.task.acceptance.measured.objective.v1` still reads `output_verified`
   and leaves `DEFINITE_DEBT` only when run against a real receipt.

## 5. Receipts

```
python3 one_example_is_a_point_a_test_is_a_quantifier_probe_20261112.py --list
python3 -m pytest -q canonical/tests/test_one_example_is_a_point_a_test_is_a_quantifier_v1.py  7 passed
```

## 6. Non-claims

One fixture, one generator, single-mutation candidates only. The absolute counts are a property of
this small space; the *ratio* is the claim, and it is illustrative rather than universal. In the
space of all programs one demonstration also leaves infinitely many survivors, but that is an
argument from the definition of a function, not a measurement, and this note only reports what was
counted. No capability registered, no repository state touched, `truth.achieved` false, $0, zero
model dependency.

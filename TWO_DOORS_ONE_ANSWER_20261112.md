# Two doors, one answer

**Measured 2026-11-12 on `144f4ab9`.** Instrument: `canonical/tools/two_doors_one_answer_v1.py`.
Record: `canonical/verification/TWO_DOORS_ONE_ANSWER_20261112_V1.json`. Tests:
`canonical/tests/test_two_doors_one_answer_v1.py` (20).

The owner restated the problem in its hardest form: *"what we've built is NOT a solution to
generalization. It's a limited lookup system. Our semantic generalization can only handle tasks with
very similar wording. It cannot: count different things, work on different files, handle different
task structures, actually understand what it's doing."*

Four charges. Two are false, one is true but for a reason that is not the one stated, and one is true
and is the real answer — and none of the four is "we need to train a model."

---

## 1. The probe

Nine sentences, two front doors, ground truth computed by `ast` in-process rather than taken on trust.

| sentence | truth | `solve()` | `run_raw_goal()` |
|---|---:|---:|---:|
| count functions `solve_v1.py` | 9 | **9** | 9 |
| functions `astra_runtime.py` | 153 | **153** | 155 |
| classes `astra_runtime.py` | 2 | **2** | 155 |
| classes `goal_compiler.py` | 2 | **2** | 150 |
| functions `goal_compiler.py` | 148 | **148** | 150 |
| list functions `solve_v1.py` | 9 names | **9 names** | `None` |
| list classes `astra_runtime.py` | 2 names | **2 names** | `None` |
| functions `errors.py` (0 functions, 3 classes) | 0 | **0** | **3** |
| classes `errors.py` | 3 | **3** | 3 |

**Primary door 9/9. Secondary door 2/9.** (The nine function names, for the record:
`_default_staging_path`, `_snapshot_small_tree`, `_solve_impl`, `_stage_or_crystallize_paired_skill`,
`act`, `observe`, `read`, `render`, `solve`.)

## 2. Why this is the sharpest possible demonstration

`solve_v1.py` declares **9 functions and 0 classes**. `python_source_definition_count.py:137` computes
`total = functions + classes` and returns that as `answer`. On `solve_v1.py`, `9 + 0 == 9`, so the sum
and the count are the same integer and **the published demonstration is correct by arithmetic
coincidence**. Ask the same machine about a file where the two differ and it is wrong every time:

* `astra_runtime.py` — 153 functions, 2 classes. Asked for classes → **155**.
* `errors.py` — **0** functions, 3 classes. Asked for functions → **3**. A file with no functions at
  all, answered with the class count.

The rule is exact and was confirmed on all seven count probes: **the secondary door is right if and
only if the quantity asked equals `functions + classes`.** That is the signature of an unbound answer
slot, not of a lookup table.

## 3. The fix already exists, on the other door

`canonical/runtime/answer_shape_v1.py` already contains the reconciliation, and its docstring already
names the defect:

> *"When `python.source.definition_count.v1` reports `function_count`, `class_count` and
> `definition_count` together, a sentence asking specifically for functions (and not classes or
> definitions) receives `function_count` ..."*

`solve()` calls `lift_named_answer` before delivering and is 9/9. `run_raw_goal()` — the door
`INSTANT_LEARNING_PROOF.md` was produced from — never received it. This is not a missing mind; it is a
**second entry point that missed a change**, which is why the answer is one function call wide.

It is also why `PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED` sits on top of a wrong
number: verification checks `output_verified`, not whether the number answers the sentence. The tree
knows this too — `answer_shape_v1`'s own module docstring records that *"seven of the twelve PASSes
were wrong answers"* when the reconciliation was absent.

## 4. The four charges, judged

**"Cannot count different things." — TRUE, and it is the real defect.** Not because there is a lookup
table, but because the quantity named in the sentence is dropped between the sentence and the
adapter's `answer` field. `goal_compiler.py` contains no reference to `definition_count` or `classes`
at all, so nothing on that path binds the asked quantity to a returned field.

**"Cannot work on different files." — FALSE.** `ACROSS_ENVIRONMENTS_20261112_V1.json`, measured last
round: **0.548** of the work on other files of the same repository, **precision 1.000, 0 wrong.**

**"Cannot handle different task structures." — FALSE at this resolution.** Same record: **0.573**
across *different repositories*, **precision 1.000, 0 wrong**, 0.845 with three demonstrations.

**"Needs actual model training / conceptual understanding / reasoning." — TRUE as a description, wrong
as a prescription.** `GENERAL_COGNITION_SUBSTRATE_AND_CAPABILITY_OWNERSHIP_LAW_V4.md` forbids
model-produced cognition on any credited path, and the tree's ten `H100_ZERO_LEARNED_*` records are
from-scratch, standard-library-only runs with `persistent_learned_bytes: 0`. Training is not the
admissibility question and not the measured bottleneck. The bottleneck in front of you is a
**delivery defect that costs one function call** — and a second door that keeps publishing the old
number.

## 5. The limiting factor, from first principles

The machine, on the door it actually reconciles, **answers the quantity asked, enumerates when asked to
enumerate, and returns zero for zero.** What it does not do is guarantee that every entry point passes
through the same reconciliation before a `PASS` is issued. That is not a capability gap. It is the
same class of defect as the one recorded at the head of this round's own instrument — the printed
verdict read from the envelope instead of the stdout, one layer down.

Which gives the true sentence to hold onto: **the remaining work is not to make the system think
harder, it is to make it impossible for a `PASS` to exist without an answer that answers.** The
cross-environment round already found the same shape at the other end — precision 1.000 *within* a
learned change kind and 0.0 on unlearned ones. Both are interface defects. Neither is a missing mind.

## 6. What this round did not do

It did not change `run_raw_goal`, `python_source_definition_count.py`, or `answer_shape_v1.py`. The
two doors disagree, and which one is the contract is a decision for the owner, not for this
instrument. Pinning the disagreement — and making it unpublishable to claim otherwise — is the honest
first step; rewiring a primary entry point under a measurement round is how a good number becomes a
second wrong one.

Authority **NONE**. `$0`, zero model calls, no capability registered, `truth.achieved` stays `false`.

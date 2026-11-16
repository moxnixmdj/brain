# What a pass is worth

**Measured on this repository's own code, its own unedited test files, and its own mutation
engine. $0, no model, no network, no synthetic data. Producer-run. `truth.achieved` stays false.**

The question this answers is the one the last document left open. If "do it once, keep it
forever" fails because the missing object is *the verdict*, then the only thing that decides
whether a learned thing may be kept is what a verdict is actually worth. So: take a real test
suite, hand it code that is wrong, and count.

---

## 1. The two numbers

16 module/test pairs, 96 behaviour-altering candidates produced by this tree's own mutation
engine, each candidate run against the pair's real, unedited test file in a fresh interpreter
with the candidate installed under the module's own import name.

| quantity | value |
|---|---|
| candidates | **96** |
| rejected by the real test suite | **77** |
| **a pass is worth, at most** | **0.8021** |
| the suite let through (wrong code that passes) | **19** |
| rejected by a law confirmed on the pristine module | **0** |
| where a confirmed law was pointed at the mutated function | **19 of 19** |
| pairs where a law could speak at all | **2 of 16** |

Read the middle row as the answer: **on this tree, a passing suite rejects 80.2% of
behaviour-altering candidates.** The pairs varied from 1 of 6 (`skill_recheck_v1`) to 6 of 6 (six
pairs) — a pass is a coverage certificate whose value is the suite's reach, not a property of the
word "passed".

The last three rows are the second answer, and it is a zero: **of the 19 wrong candidates the
suite accepted, a law confirmed on the code as it stands rejected none** — and it was not for
lack of trying, because in all 19 of 19 cases a confirmed law was pointed directly at the
function that had been mutated.

## 2. Why the zero is not a broken instrument

The first version of this measurement produced the same zero, and it was *three instrument
defects deep*. Each was found because the zero was suspicious, not because the answer was
disappointing, and each is now a test in the tree:

1. **The interpreter was wrong.** A relative `.venv/bin/python` was resolved with
   `Path.resolve()`, which follows the virtualenv symlink into the base interpreter. Every suite
   then failed with "No module named pytest" — reported as *unrunnable*, which a careless harness
   would have counted as a pass.
2. **The trace hook had the wrong name.** `pytest_session_finished` is not a pytest hook, so the
   suite ran, passed, and wrote nothing. "No arguments were recorded" looked exactly like "the
   suite never called this module".
3. **The reduction deleted the helpers.** To execute a module without executing its module-level
   effects, the instrument rebuilt it from the definitions under test — and dropped everything
   else. A function that called a helper then raised `NameError`, and a raising function reports
   *not applicable* for every law. That silence read as "this code has no laws". Keeping
   definitions instead (safe: a `def` executes nothing but its decorators and defaults) then made
   whole modules unloadable, 43 of 121 of them, which is why the loader now falls back to
   statement-by-statement loading and records what it could not define.

With all three fixed, the numbers above are what remains. The zero is the finding.

## 3. What the zero is made of

The measurement keeps a census of every law it proposed, per pair, per arm. On 16 pairs:

| law kind | proposed | confirmed | refuted by the code itself | not applicable |
|---|---|---|---|---|
| TOTALITY (*"it ran"*) | 120 | **71** | 0 | 49 |
| IDEMPOTENCE | 65 | 2 | 7 | 45 |
| INVOLUTION | 65 | 0 | **20** | 45 |
| COMMUTATIVITY | 42 | 0 | 3 | 34 |
| ASSOCIATIVITY | 42 | 0 | 0 | 42 |
| PERMUTATION_INVARIANT | 65 | 0 | 0 | 65 |

*(invented-grid arm; the arm using the arguments the suite itself passed gives 51 / 2 / 20 / 6 / 0 / 0 — the same shape.)*

Four facts fall out, and they are the whole answer:

**The only law that confirms on real code is the one a pass already implies.** 71 of 120
proposals confirm, and they are *totality*: the function returned instead of raising. But a suite
that passed cannot have had a call raise on the inputs it executed — so on those inputs totality
is not evidence, it is a restatement of the pass. Where it is not a restatement (an input the
suite never tried) it needs a different grid, and on that grid these functions are not applicable
at all.

**The laws that could say something new are false about this code.** Involution is refuted 20
times; idempotence 7; commutativity 3. A relation invented from a function's *name* is usually
not a law of the function's *behaviour*. Finding the relations that are true is not a matter of
searching harder over shapes: it requires knowing what the function means.

**A law can only address the code it can name.** The laws cover top-level functions; in this tree
much of the behaviour sits in methods. The mutation engine duly produced mutants such as
`Localization.localized` — a method — and no law in this vocabulary can be pointed at a method.

**And even when it is pointed at the right function, it does not fire.** In 19 of 19 survivors a
confirmed law was brought to bear on the mutated function and returned the same answers as the
original. The mutation changed behaviour that the law's confirmation inputs could not see. That
is identifiability, in the small: two programs that agree on everything observed are one program
as far as any observer is concerned.

## 4. What this does to the claim "do it once and keep it forever"

The claim has two halves, and this measurement separates them cleanly.

**The half that is right.** Where a real suite exists, a pass is strong evidence: 80.2% of wrong
behaviour is rejected here, and this tree's suites are *stronger* than the field's agent-authored
tests (26 of 500 SWE-bench Verified tasks had tests that accepted wrong patches after expert
human screening^[UTBoost, ACL 2025 — [ddkang.substack.com](https://ddkang.substack.com/p/swe-bench-verified-is-flawed-despite)]^;
80.2% of 86,156 agent-authored test-file patches carried weak or no oracle signals^[arXiv:2606.18168 — [arxiv.org/abs/2606.18168](https://arxiv.org/abs/2606.18168)]^;
more than 15% of Verified instances have test patches loose enough for incorrect or partial
solutions to pass^[arXiv:2503.15223, reported in [aiwiki.ai/wiki/swe-bench_verified](https://aiwiki.ai/wiki/swe-bench_verified)]^).
So "one experience, verified by a real suite, kept" is worth a lot — *proportional to that
suite's coverage, and no more*.

**The half that is false.** The permanence. What you keep is exactly what the verdict could
distinguish, and a verdict built from the program's own shape can distinguish *nothing* that a
pass has not already distinguished — measured: 0 of 19. In a new environment the suite is gone;
what remains is the shape, and the shape is worth 0 on top of a pass and 11.4% on its own
(re-measured with the fixed instrument: 12 of 105 variants rejected by a law, 73.3% invisible —
receipt `SPECIFICATION_FROM_STRUCTURE_20261116_V2_REDUCTION_FIXED.json`). That is the
insufficiency certificate, no longer an argument: it is a census with a number next to every kind
of law this vocabulary can express.

## 5. The three challenges, answered by this measurement rather than by prose

**Identifiability.** 19 survivors, a confirmed law pointed at the mutated function in every one,
zero kills. Two programs agreeing on every input the law was confirmed on are indistinguishable
to it. The challenge is not hypothetical; it is the residual row of the table in §1.

**The insufficiency certificate.** It is the census in §3. The vocabulary can express six
relations; five of them are refuted or inapplicable on real code; the sixth is implied by any
pass. A verifier built from shape is insufficient *by construction*, and now by measurement.

**The synthesis–verification asymmetry.** The asymmetry is smaller here than the field's and it
does not help: this tree's suites do reject 80.2% of what is wrong, yet the part a verifier could
add (the 19) is exactly the part no shape-derived law can see. The asymmetry is not "tests are
weak" — it is "the verdict's reach is the reach of the knowledge inside it".

## 6. The smartest next moves, ranked, each falsifiable

1. **Attach a verdict budget to every learned thing.** A lesson admitted against a suite is
   admitted *with that suite's measured worth* (80.2% here; 1/6 on `skill_recheck_v1`). Nothing
   in this tree currently carries that number with it, which is how "learned permanently" quietly
   becomes "learned against whatever happened to be tested". Cost: one field and one measurement
   per admission. Falsifier: lessons whose measured worth does not predict their failure rate on
   later tasks are not being measured at all.
2. **Take the vocabulary from assertions, not from names.** The relations that survive contact
   with real code are the ones that name what the code means. The test files in this tree already
   contain such relations, expressed as assertions (`material_differences(a, b) != ...`,
   `usable(...) after expire_stale(...)` is false). Generalising an *assertion the suite already
   makes* into a law over a wider grid is a real research direction, unlike inventing relations
   from `def normalize(`.
3. **Move the laws to methods — that is where the behaviour and the weakness both are.** Six of
   16 pairs are fully defended (6/6) and one defends 1/6; the mutants that survive are
   disproportionately in classes. A vocabulary that cannot name a method cannot help there.
4. **Ship the survivor list, not just the rate.** The most valuable output of this instrument is
   the 19: wrong candidates that a real suite accepted, each with the mutation that produced it.
   That is a coverage report for the suite, which is a test-synthesis target with a ground truth
   attached — the one place in this tree where "write the missing test" has a known answer.

## 7. What is not real here

- A kill is not a proof and a survivor is not an approval. `ACCEPTED_BY_BOTH` means *nothing
  available falsified it*.
- The 80.2% is about **this** tree's suites, not about software in general. It is high here
  because these modules are small, pure, and were written with tests beside them — which is also
  why the laws had so little room.
- The mutation engine mutates; it does not model a real bug. A mutation score is a lower bound on
  what a suite can catch for the mutations sampled, and no kind of correctness proof.
- Six pairs were skipped by name and counted: five whose suite does not pass on the pristine code
  and one that takes longer than 20 s. None of them was skipped to make a number look better, and
  the skipped list is in the receipt.
- Nothing here was produced by a model, and no number here is a capability claim.

---

### Artifacts

| what | where |
|---|---|
| verdict kernel (two gates, trace, recorded grids, law census) | `canonical/swe_kernel/patch_verdict_amplification_v1.py` |
| structure kernel (reduction and loader fixed this session) | `canonical/swe_kernel/specification_from_structure_v1.py` |
| the harness that produced the numbers | `canonical/tools/patch_verdict_amplification_measure_v1.py` |
| receipt, amplifier | `canonical/verification/PATCH_VERDICT_AMPLIFICATION_20261116_V1.json` |
| receipt, structure re-measured with the fixed instrument | `canonical/verification/SPECIFICATION_FROM_STRUCTURE_20261116_V2_REDUCTION_FIXED.json` |
| the earlier answer (kept, for the argument this one measures) | `THE_VERIFIER_IS_KNOWLEDGE_NOT_LEARNING_20261116_V1.md` |

Reproduce: `.venv/bin/python canonical/tools/patch_verdict_amplification_measure_v1.py --max-pairs 16 --max-mutants 6`

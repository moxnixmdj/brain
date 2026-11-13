# The wall is in the vocabulary, and it can now be proved

**Date:** 2026-11-13 **Branch:** `arena/15c3bce3-brain`, base main `e5be642e` **Authority:** NONE — producer-run measurement in one sandbox, not independent verification
**Modules:** `canonical/runtime/applicability_v1.py` (`insufficiency_witness`), `canonical/runtime/world_probe_v1.py` (`_FILE_NAME_PREFIXES`), `canonical/runtime/fact_entailment_v1.py` (three-component specs)
**Instrument:** `canonical/tools/insufficiency_certificate_probe_v1.py` · **Tests:** `canonical/tests/test_insufficiency_witness_v1.py` (12), `canonical/tests/test_a_test_corpus_is_a_naming_convention_not_a_substring_v1.py` (12)

## 0. The owner's question, answered

*"Instant learning + instant learning in new arbitrary environments — we already solved those perfectly. Doesn't this mean this is a perfect solution for all problems and any computer using? … Is this true, or are there things that are wrong?"*

**No, and this round proves the "no" instead of asserting it.** `applicability_v1.insufficiency_witness` is a proof, in `|evidence|` set comparisons, that a body of experience **cannot** yield a requirement — no matter how many more times the same kind of run is repeated. Run on this tree's own pinned real code-repair corpus, it fires. So "do it once and it is learned forever" is not merely unproven for that case; it is **refuted**, with a certificate, and the certificate names what would have to change.

On the pasted weight-space analysis: **the four citations are real, and three of them say the opposite of what the paste concludes.** I checked the load-bearing one myself rather than borrowing the concurrent round's table — ASCENT, arXiv:2610.05303 (Lu & Gong, UNSW, 4 Oct 2026): LoRA fast weights self-distilled from a frozen copy of the model reading its own verified trajectory with hindsight; **>22 points** exact success over base on ALFWorld/WebShop at both scales, 69.5% ± 5.6 vs 46.4% base; transfers to held-out scenes. And its own stated limits: it **requires open weights and full next-token distributions**, it **skips the update when an episode fails**, and —

> *"One verified success does not reveal which individual turns caused success, or whether an untried alternative would have been better."*

That is the same limit this round makes decidable in a token-space setting. ASCENT can only note it; `insufficiency_witness` **proves it or disproves it for a given body of evidence**, and says whether more runs of the same kind could ever help. This repository has no open weights, no next-token distributions and a standing zero-model-dependency rule, so weight-space consolidation is not a route available here — and the source the paste cites for "add weights now" (the AWS continual-learning spectrum) is a **persistence/cost** ranking whose own decision tree reads *"Do you run your own model? No → loop engineering + memory (max out scaffold first)"*. The scaffold is what this round fixed.

## 1. The certificate: when experience provably cannot teach

`learn` already refuses to invent a requirement and answers `INCONSISTENT`. The refusal was unexplained on real code, because the instrument built to explain it — `vocabulary_gap` — fires only when two observations have **equal** fact sets. Measured on the four pinned historical repairs, judged by their own upstream test suites:

| | facts | sites | candidates | executed verdict |
|---|---|---|---|---|
| `unit_boundary` | 10 | 9 | 9 | REPAIRED |
| `bits_capacity` | 7 | 4 | 4 | REPAIRED |
| `ichunked_zero` | 45 | 56 | 32 | FIRED_AND_NOT_REPAIRED_WITHIN_BUDGET |
| `chunked_even_zero` | 45 | 56 | 32 | FIRED_AND_NOT_REPAIRED_WITHIN_BUDGET |

`vocabulary_gap` → **None** ("nothing is wrong with the vocabulary"), while `learn` → **INCONSISTENT, 0 survivors**. Both correct, and together useless: the tree could say *nothing can be learned here* and *nothing is wrong* at the same time.

**The certificate.** Write `A` = the intersection of the fact sets of all successes. A conjunction of observed facts is consistent with the successes exactly when it is a subset of `A`, so `A` is the largest candidate; and it excludes a failure `F` exactly when it is *not* a subset of `F`. Therefore:

> **no requirement exists ⟺ A ⊆ F for at least one failure F**

`learn` reaches that verdict by enumerating all `2^|A|` subsets and finding none alive. The certificate reaches it in `|evidence|` set comparisons — which also means it **decides cases where `learn` must answer `BOUNDED`** because `|A|` exceeds its cap of 12. Verified exhaustively, not sampled: **2517** evidence sets over a three-fact vocabulary, **0** disagreements with `learn`; **820** equal-facts cases, **0** disagreements with `vocabulary_gap`, whose shape this strictly subsumes (equal facts make `A` a subset of that failure).

**On the real corpus it fires**, with `kind = SEPARATION_IMPOSSIBLE`, and the two facts every success shares are

```
baseline.violates_own_spec    operator.Gt
```

— which are **exactly** the two facts Round G's `constant_facts` reported as constant across all four observations. So the sharpest form of the finding is: *the only facts the successes agree on are facts the failures also have.* Nothing in this vocabulary separates a repairable target from a non-repairable one, and `unrepairable_by_repetition: True` — more runs of the same kind report the same fact vector forever. Only a new observable helps.

The certificate also separates two refusals that look alike and are not: a **missing kind of observation** (no failure, no success, no evidence — `unrepairable_by_repetition: False`, more runs *do* help) from a **missing observable** (`False` → `True`, more runs cannot help). That distinction is the whole content of "show it once".

## 2. A correction to something I shipped in Round G

Round G's merged claim stated the obstruction as *"the failures' site-fact sets (45 facts each) are supersets of the successes' (10 and 7)"*. **Measured, that is false for all four pairs** — no individual success fact set is a subset of any failure's. The true obstruction is narrower: the *intersection* of the successes is contained in every failure. The difference is not pedantry — the broad form would predict that any single success's facts discriminate, and a repair aimed at that would have been wrong. `test_correction_no_success_fact_set_is_a_subset_of_a_failure` now pins both halves so the wrong statement cannot be re-shipped.

## 3. A live vocabulary defect on main, and the trap inside its repair

`world_probe_v1` decided `python.test.corpus` by asking whether the lowercased **relative path** contains `"test"`. Two loosenesses compound: `"test"` is read out of the middle of an ordinary word, and out of a **directory name**, so every `.py` under a directory merely named `tests` announced itself as a test module. Measured on this tree: **2662** files matched, **2608** are genuine `test_*.py` modules, so **54 files (2%)** announced a test corpus that is not one — 29 via a directory component, 25 via the filename:

```
canonical/runtime/attested_state_v1.py                      "at-TEST-ed"
canonical/runtime/bound_capabilities/python_test_audit.py   a capability ABOUT tests
canonical/tools/seeded_faults_tests_as_the_judge_v1.py      a probe, not a test
canonical/tests/fixtures/.../before.py                      a DEFECTIVE fixture, under a path containing "tests"
```

This was not cosmetic. `python.test.corpus.available` is a declared precondition of test-guided capabilities (`python.fault.localize.dynamic.dataflow.v1`, `python.patch.search.test_guided.ast.v1`), so a directory with no tests could ground a capability that then has nothing to be guided by. And it made **`canonical/tools`, holding zero genuine test modules, sense as IDENTICAL to `canonical/tests` and to `canonical/verification`** — the equal-facts wall, live on the real tree.

It left `canonical/tests/test_real_input_space_census_v1.py` **red on main for about three hours**: PR #6814 pinned `canonical/tools: False` at 00:10 UTC, and two other rounds added `*tests*`-named tools at 00:42 and 00:56. That suite ships two checks the repository's growth had made **mutually unsatisfiable** — one compares the sensor to genuine `test_*.py` counts and says divergence means *"the learned requirement is unsound on the real tree"*, the other pinned the substring behaviour with a comment naming this exact fix and declining to ship it: *"The fix (require the stem to start with `test_`) is a narrowing of a sensor every binding decision reads, so it is named, not shipped blind."* Narrowed, both pass, and that pinned assertion plus its docstring were updated in the same commit as its own comment authorized.

**Before and after, on the census the tree already ships:**

| | learn | survivors | certificate | older witness |
|---|---|---|---|---|
| before | `INCONSISTENT` | 0 | `SAME_OBSERVED_STATE_OPPOSITE_OUTCOMES` | FIRES |
| after | **`IDENTIFIED`** | **1** → `python.test.corpus.available` | None | — |

and the identified requirement admits every real success and refuses every real failure. Blast radius: **10 of 101** directories with `.py` files change verdict, every one in the obviously-correct direction (fixtures and evidence files stop being tests; `canonical/astra_runtime` and a vendored package start being credited for genuine modules they hold).

**The trap, and why it is the part worth the diff.** `fact_entailment_v1` derives its implication relation *from the sensor's own spec table*, so that the two can never drift. Moving the constraint out of that table into a separate prefix map made `python.test.corpus` **spec-identical to `python.source`** — so the relation declared them **equivalent**, and `reduce_requirement` canonicalised the census requirement to `python.source.available`. A capability declaring a test corpus would then have been grounded by *any directory holding Python source and no tests at all*: narrowing the sensor silently **widened** what the tree believes. Specs now carry the prefix as a third component and the entailment reads it. Measured after the repair: 19 known facts, **33** implication pairs (unchanged), `corpus ⇒ source` **True**, `source ⇒ corpus` **False**, equivalent **False**.

Two further gaps a mutation run exposed are recorded rather than hidden. A prefix tested against the whole path is indistinguishable from one tested against the filename for any single-directory root, because the sensor indexes paths *relative to the root* — only a **nested** module separates them, and no test had one. And the prefix arm of `_spec_implies` is **unreachable from the live table** while exactly one kind carries a prefix, so it is now exercised directly on constructed specs; it becomes load-bearing the moment a second prefixed kind exists.

## 4. What a vocabulary repair for the real corpus would cost

Closing the code-fact vocabulary to kinds and emitting **absence** for every kind not present does remove the obstruction — the certificate stops firing. But the shared literal set grows to **23**, so **2^23 = 8,388,608** hypotheses against a learner cap of **12**, and `learn` answers `BOUNDED`. The obstacle moves from **representation to combinatorics**, which is a different problem with a different repair (compute minimal hitting sets instead of enumerating, or move the unit of observation from target to site, where a site's fact set is small). This round measures that decomposition and stops there rather than shipping "add negation" as if it were the end of it.

## 5. What this does NOT claim

- **Not** that the real code-repair corpus can now be scoped. It cannot: the certificate fires, and `unrepairable_by_repetition` is `True`. Round G's `INCONSISTENT` stands, now with a proof attached.
- **Not** that absence facts are shipped. Section 4 measures their cost; nothing in the learner changed.
- **Not** that `*_test.py` is a test module here. pytest collects it, but the tree's own check defines genuineness as `test_*.py`; accepting both would reintroduce divergence for any directory holding only the suffix form. This tree has none, so the narrower rule loses nothing.
- **Not** a weight-space result, and **not** a benchmark number. No model was called; every verdict is an executed test suite, a filesystem scan, or a set comparison.
- **Not** that the shipped skill corpus has scopes: the ledger is unchanged at 5 of 5 `EXACT_MATCH_ONLY`.
- **Not** independent certification of anything: `authority NONE`, one sandbox.

## 6. A red guard on main that this round did not touch, reported not fixed

`canonical/tests/test_computer_unconfined_route_guard_v1.py::test_controller_does_not_run_unconfined_query_or_archive` **fails on clean main**, verified by stashing every change in this round and re-running: `assertFalse(result['pass'])` fails with *"True is not false"* for the goals `count lines in notes.txt` and `pack notes.txt into notes.tar.gz`. The controller now returns `pass=True` where this guard requires `BLOCKED` and no unconfined `answer_query` / `perform`. Either the controller gained a confined path and the guard's expectation is stale, or it now serves those goals unconfined — and telling those apart needs the controller read end to end, which is its own round on a safety guard, not a drive-by edit. It is named here so it is not lost. **303 passed, 3 skipped, 1 pre-existing failure** across every suite that reads the three changed modules plus the confinement and dispatch guards.

## 7. Verification

- `canonical/tests/test_insufficiency_witness_v1.py` — **12 passed**: the exhaustive equivalence (2517 sets, 0 violations), subsumption (820 cases, 0 violations), the real corpus, the positive control where separation *is* possible, both `BOUNDED` directions, the missing-kind refusals, the absence-cost decomposition, and the Round G correction
- `canonical/tests/test_a_test_corpus_is_a_naming_convention_not_a_substring_v1.py` — **12 passed** in 0.42 s: both directions of the convention, the nested module, the directory-name half, the real tree, the pinned configuration, the entailment, and the non-empty-relation guard
- `canonical/tests/test_real_input_space_census_v1.py` — **9 passed**, red on main before this round
- Batch — **303 passed, 3 skipped**, 1 pre-existing unrelated failure (§6)
- Mutations — **12 of 12 killed**, 9 on the first run and 3 after the gaps they exposed were closed
- Instrument — `python3 canonical/tools/insufficiency_certificate_probe_v1.py` reproduces every number above in ~15 s, `$0`, no model, no network, nothing written

## 8. Reproduction

```bash
python3 canonical/tools/insufficiency_certificate_probe_v1.py          # the whole measurement
python3 canonical/tools/insufficiency_certificate_probe_v1.py --json
python3 -m pytest canonical/tests/test_insufficiency_witness_v1.py \
                canonical/tests/test_a_test_corpus_is_a_naming_convention_not_a_substring_v1.py \
                canonical/tests/test_real_input_space_census_v1.py -q
```

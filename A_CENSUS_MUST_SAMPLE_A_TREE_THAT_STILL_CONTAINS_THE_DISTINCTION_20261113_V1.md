# A census must sample a tree that still contains the distinction

**Date:** 2026-11-13 **Branch:** `arena/15c3bce3-brain`, base main `8cb35f65` **Authority:** NONE — producer-run measurement in one sandbox
**Files:** `canonical/tests/test_real_input_space_census_v1.py` (test-only), `canonical/tests/test_a_test_corpus_is_a_naming_convention_not_a_substring_v1.py` (test-only)
**No runtime module changed in this round.**

## 0. What happened

PR #6863 merged at 04:24 UTC. On the merged tree, two of its own tests were red — tests that were green on the branch minutes earlier. Not a bad merge:

```
FAILED test_real_input_space_census_v1.py::test_the_existing_sensor_separates_success_from_failure_on_real_outcomes
FAILED test_a_test_corpus_is_a_naming_convention_not_a_substring_v1.py::test_canonical_tools_has_no_test_corpus_and_canonical_tests_does
```

Two concurrent rounds had added **genuine** `test_*.py` modules to `canonical/tools` — `test_entry_point_finder_v1.py` (`ee9685dd`, 1 test function) and `test_oracle_strength_measure_20261113_v1.py` (`97684727`, 5 test functions). `canonical/tools` held zero when #6863 pinned it. So the sensor was **right** and the pins were **stale facts about the tree**.

The interesting part is that the first failure was not a red assertion about `canonical/tools`. It was silent, and worse:

## 1. The census degraded without going red where it mattered

Flip the stale pin to the measured value and re-run the learner:

| evidence | learn | survivors | `most_general` |
|---|---|---|---|
| as pinned (`tools: False`) | `INCONSISTENT` | 0 | — |
| as measured (`tools: True`) | **`AMBIGUOUS`** | **2** | **`python.source.available`** |

The census's six directories were chosen so that *source-but-no-tests* was the unique failure. `canonical/tools` was that directory. Once it genuinely grew tests, five of six directories were successes and the **only** remaining failure was `canonical/analysis`, which holds **no Python at all**. `python.source.available` then separated the evidence too — and since `corpus ⇒ source`, source is the *weaker* fact, so it became `most_general`. The census kept passing its admits-check while **identifying the wrong requirement**.

That is the failure mode worth naming: a measurement can stop measuring without any assertion about the thing it measures going red.

## 2. The repair, and why the sample is derived rather than chosen

Hand-picking a replacement failure directory would be selecting evidence to make a test pass. So the sample comes from a rule that **never mentions tests** — every directory under `canonical/` at depth ≤ 2 holding Python source directly — and the outcomes come from an **independent** `rglob("test_*.py")` count. Measured:

```
structural candidates: 13        with tests: 7        source but no tests: 6
python.source.available present in 13/13   json 9/13   markdown 6/13
learn -> IDENTIFIED__ONE_CONSISTENT_REQUIREMENT   survivors 1
most_general -> ['python.test.corpus.available']  admits == oracle on all 13   disagreements 0
```

`canonical/swe_kernel`, the directory the previous round used as its genuine failure, is no longer one: it holds a `test_*.py` now. The six that remain are `canonical/evidence`, `canonical/experiments`, `canonical/integrations/brain_fabv2_native_v1`, `canonical/obsolescence`, `canonical/research/bytes`, `canonical/swe_kernel/taught_actions`. The tree chose them.

Two guards pin **why** identification holds instead of assuming it:

1. both outcome classes must be non-empty, or the census is vacuous;
2. **some failure must hold Python source**, or the weaker source fact separates too and wins.

## 3. The first version of guard 2 was wrong, and a scenario check caught it

I wrote guard 2 as *"every sampled directory must hold Python source"*. A four-scenario check refuted it:

| scenario | guard 1 | guard 2 (first version) | identifiable? |
|---|---|---|---|
| the real sample | ✓ | ✓ | ✓ |
| every directory holds tests | ✗ | — | ✗ `UNDETERMINED` |
| real sample **plus** a Python-free directory | ✓ | ✗ **fires** | ✓ **still IDENTIFIED** |
| only a Python-free failure | ✓ | ✗ | ✗ `most_general = source` |

Row 3 is a **false positive**: injecting a Python-free directory into a sample that already has source-holding failures changes nothing, because `source` excludes a failure only if that failure lacks source. The census degraded on 2026-11-13 **only because its single remaining failure was Python-free**. The guard is now the condition that actually decides it, and the four rows agree with identifiability exactly.

Both guards live in module-level helpers that the census **and** the synthetic equivalence test call, so a mutant that makes either guard stricter or weaker is killed rather than silently restated.

## 4. Mutation results, including the survivor

`4 of 5 killed`:

| mutant | verdict |
|---|---|
| guard 2 → `all(source in states[d])` — **the bug I actually made** | **KILLED** |
| guard 2 → `any(not real[d])`, ignoring source | KILLED |
| guard 1 → drops the failure-side check | KILLED |
| sample rule cherry-picks directories that have tests | KILLED |
| **the `rglob` oracle replaced by the sensor's own verdict** | **SURVIVED** |

The survivor is irreducible from inside the file and is recorded rather than papered over: on this tree the sensor and the independent count agree everywhere, so making the comparison tautological still passes. **Oracle independence is a property of the code path, not something an assertion can enforce.** What catches a sensor defect is the sibling suite, which builds directories whose names and contents disagree and pins both directions.

## 5. A stale tree fact is not an invariant

`test_canonical_tools_has_no_test_corpus_and_canonical_tests_does` was deleted and replaced by `test_the_sensor_agrees_with_an_independent_count_on_real_directories`, which asserts the durable property — sensor verdict equals independent count, **in both directions**, on whatever the tree holds now — and requires both directions to be represented, or the agreement proves nothing.

This is the second time in two rounds this census broke because the tree grew: first under the substring rule, now under genuine test modules. The first was a sensor defect; this one was a **sample** defect. Both are now pinned by construction rather than by enumeration.

## 6. What this does NOT claim

- **Not** a runtime change: no module under `canonical/runtime/` was touched; `world_probe_v1`, `fact_entailment_v1` and `applicability_v1` are exactly as #6863 merged them, and its 12-of-12 mutation result stands unchanged.
- **Not** that `canonical/tools` should hold no tests. It holds two genuine ones now and is correctly credited.
- **Not** that the six source-without-tests directories are permanent. They are the tree's current answer; the sample is derived, so it follows the tree instead of breaking on it.
- **Not** that the census is tamper-proof: §4's survivor says exactly where it is not.
- **Not** independent certification: `authority NONE`, one sandbox.

## 7. Still open, unchanged

The pre-existing red guard on main that #6863 reported and did not touch: `test_computer_unconfined_route_guard_v1.py::test_controller_does_not_run_unconfined_query_or_archive` fails on clean main (`assertFalse(result['pass'])` → *"True is not false"* for `count lines in notes.txt` and `pack notes.txt into notes.tar.gz`). Deciding whether the controller gained a confined path or now runs unconfined needs the controller read end to end — its own round on a safety guard.

## 8. Reproduction

```bash
python3 -m pytest canonical/tests/test_real_input_space_census_v1.py \
                  canonical/tests/test_a_test_corpus_is_a_naming_convention_not_a_substring_v1.py \
                  canonical/tests/test_insufficiency_witness_v1.py -q      # 35 passed
```

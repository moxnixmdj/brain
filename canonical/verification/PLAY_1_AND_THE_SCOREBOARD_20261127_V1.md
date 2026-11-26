# Play 1, step 1, and the exact-target scoreboard — 2026-11-27

Two things were run this round, both of them reads or small executions with no model and no
network: the adapter derivation that Play 1 called for, and the scoreboard that two rounds of
plans asked for. One was killed by its own floor; the other produced the first exact-target
routing numbers in this repository, and they are worse — and more useful — than expected.

**Instruments:** `canonical/tools/ast_adapter_derivation_v1.py`, `canonical/tools/exact_target_scoreboard_v1.py`
**Artifacts:** `PLAY_1_LITERAL_CALL_CENSUS_20261127_V1.json`, `EXACT_TARGET_SCOREBOARD_20261127_V1.json`
**Tests:** `canonical/tests/test_exact_target_scoreboard_v1.py` (5 pass)

---

## 1. The adapter derivation: KILLED at 3.7 %

The rule was fixed before the run: an adapter may be derived from a module's own AST only if a
call in the module's own test has **literal** arguments; it is then executed **twice** in a
fresh interpreter, in a temp directory, with a 5 s timeout, and kept only if both runs agree.
Kill floor: 40 % survival.

| outcome | count |
|---|---:|
| `NO_LITERAL_CALL_IN_TEST` | 233 |
| `NO_TEST_FILE` | 114 |
| `CALL_ERROR` | 26 |
| `NO_PUBLIC_FUNCTION` | 18 |
| **`SURVIVES`** (both runs agree) | **15** |
| **attempted** | **406** |
| **survival rate** | **0.037** |
| **verdict** | **KILLED** (floor 0.40) |

Why it failed is visible in the data, not a mystery: tests in this tree call through module
aliases (`P.move_of(...)`, `m.minimum_proof_carrying_information_set(...)`) with constructed
arguments, or through a local helper whose inputs are built at run time. A literal-only rule
sees almost none of that.

**What survives anyway:** 15 adapters, each with a receipt — two agreeing runs, the exact
arguments, the output digest — and 15 exact targets. They are real, and they are not enough to
move a 641-module deficit.

**What this changes:** the derivation must take its arguments from an *execution*, not from the
source text. The next variant records the call frame during the module's own test run and
replays the recorded arguments. That is a different build, and it is now the first item in the
plan rather than an assumption inside it.

## 2. The scoreboard: routing measured against one module, chance 1/849

**Targets.** For every ledger `SOURCE_ONLY` module that ships a same-stem test, the query is the
test author's own statement of intent — the names of the tests, stripped of `test_` and version
suffixes, plus the test module's docstring — and the target is exactly one module path.

| quantity | value |
|---|---:|
| pool | 849 |
| targets | 404 |
| **queries that repeat the module's own name (leak)** | **310 (76.7 %)** |
| clean targets | 94 |
| chance at rank 1 / rank 5 | 0.00118 / 0.00589 |

| channel (clean, n = 94) | @1 | @5 |
|---|---:|---:|
| `find_source` | 0.032 | 0.064 |
| contract router (verbs/objects from AST) | 0.064 | 0.128 |
| **topic-only ablation (gate removed)** | **0.096** | **0.181** |

| channel (leaked, n = 310) | @1 | @5 |
|---|---:|---:|
| `find_source` | **0.332** | **0.548** |
| contract router | 0.100 | 0.268 |
| topic-only ablation | 0.100 | 0.252 |

Three findings, in order of how much they change the plan:

1. **Most routing in this repository is name matching.** On the 77 % of queries that repeat the
   module's name, `find_source` reaches 0.55 at rank 5. On the clean quarter it reaches 0.064.
   The same tell will be present in any benchmark whose queries were written by someone who
   knows the answer — which is how most retrieval suites are built.
2. **The contract router is dead, again.** Its best result (0.128 at rank 5) is beaten by the
   same scorer with the contract gate removed (0.181). Two independent corpora, two
   independent queries, same verdict: the gate is not what routes.
3. **Exact-target routing is 6–18 % at rank 5, against a chance of 0.6 %.** That is 11–31× chance
   and still useless: four in five clean requests are answered with the wrong module. The
   previous plan's premise — that the router needed a better scoreboard — is now measured: with
   a better scoreboard, the router is worse than the domain label suggested, and the ablation
   sets the bar.

**Honest limits.** The clean subset is 94 rows, so a 0.064 vs 0.181 gap is about ±5 pp at one
standard error; the direction is consistent with the previous round's 0.952-vs-0.905 but the
magnitude is not precise. And "the module the test author wrote tests for" is not always the
only sensible answer — this tree carries families of near-duplicate modules (`*_v1`, `*_v2`,
`*_20261127_V1`), so a singleton target punishes a router that returns a sibling.

## 3. What the plan becomes

1. **Targets become equivalence classes.** Score "any member of the module's family" — same stem
   with the version suffix removed, plus modules the same test file imports. Report singleton and
   family recall side by side; a channel that cannot beat the ablation on both is not routing.
2. **The adapter derivation takes arguments from an execution.** Record the call frame during the
   module's own test run, replay the recorded arguments twice; the receipt is the pair of agreeing
   runs. The literal-call variant is dead and is not to be revived.
3. **The query set needs leaks removed by construction, not by filter.** Generate intents from the
   *behaviour* the test asserts (the function it calls, the values it checks) rather than from the
   test's name, so the module's own words cannot appear in the query.
4. **Nothing above changes the deficit.** 31 callable of 849 is still the number to move, and no
   routing improvement touches it: the modules are uncallable, not unfindable.

Every number in this note is a row of the two artifacts named at the top, produced by the two
instruments named at the top, in one sandbox, with 0 model calls and 0 network calls.
Independent reproduction is open.

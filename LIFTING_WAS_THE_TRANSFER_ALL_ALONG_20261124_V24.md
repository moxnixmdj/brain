# LIFTING *WAS* THE TRANSFER — syntax crosses a boundary, ground names do not
### 2026-11-24 · branch `arena/50c05c04-brain` · 0 model calls · 0 stored parameters · 0 network

> Requirements restated: own model, zero runtime model calls; no parameter warehouses world facts; every
> parameter derived and justified; knowledge external, inspectable, removable; project then web; name the
> real limiting factor; kill the idea before building it; verified / unverified / failed; hardest real
> tests; never ask the user. §2 resolution unchanged. No model call, no stored parameter.

---

## 1. The question the prompt's store plays depend on

Every play in the prompt that involves a skill store assumes the same thing: knowledge learned in one
environment replays in another. Four rounds ago I tested that on the ten machine worlds and it failed twice
(un-lifted: 42 of 50 transferred predictions wrong; lifted: still wrong, and importing laws *degraded* the
target from 0.976 to 0.810).

But there was a confound I never isolated, and it is now measurable. Machine-world laws failed because
their keys named **ground state** (`GIT_A1`, `probe_seed_content`). Real-code vocabularies are relations
over **syntax** (`HAS_TRY`, `BRANCH_ON_CALL`, `LINES`). If the mechanism is "syntax crosses, ground names
do not", then a syntactic vocabulary should cross a codebase boundary intact — and that is testable without
a benchmark, a model call, or a Docker image.

## 2. Design

Split this repository's own Python into **disjoint top-level code-groups** (a group is a different
codebase in the only sense that matters: no file, identifier, or import is shared beyond the standard
library). Choose one vocabulary per group. Then score **every vocabulary on every other group**.

Nothing is scored on the data it was chosen from, so the pooled cross-group number is out-of-sample by
construction rather than by argument.

## 3. The result — the first verified transfer in this project

| | predictions | wrong | accuracy | coverage |
|---|---|---|---|---|
| within its own group | 380 | 4 | **0.9896** | — |
| **across to another group** | 336 | 7 | **0.9796** | 0.0305 |

**Accuracy survives the boundary — 0.9796 against 0.9896, a 1-point gap.** After two outright failures on
machine worlds, a vocabulary learned on one body of code predicts behaviour in a different body of code at
essentially undiminished accuracy.

The mechanism is identical in both directions and is now stated precisely:

> **A relation over SYNTAX crosses an environment boundary. A relation over GROUND NAMES does not.**

That single sentence explains V15 (un-lifted transfer failed), V16 (lifting helped *within* a machine but
still failed *between* them — because the lifting replaced names in the keys but left ground *content* in
the effects), and this round (syntactic relations transfer at full accuracy). It also explains why the
machine-world failure was not a dead end: it was the control condition that makes this result mean
something.

**The mission's actual claim — that lifting is the mechanism by which a store becomes portable — is
therefore supported, not refuted.** I said in V13 that "the store is not portable as it stands", and that
was too strong. The store was not portable *because it was not fully lifted*; a fully syntactic vocabulary
is.

## 4. What this does NOT establish, stated before it can be misread

* **Only 2 groups survived the filters** (≥40 files, ≥200 functions), so there are 2 ordered pairs. This is
  a demonstration, not a survey.
* **The groups are wildly unequal** — 43,628 vs 390 trained functions. The small `execution_guard` group
  supplies 380 of the 380 within-group predictions, so the "within" figure is essentially one group.
* **Coverage across the boundary is 3.05%**, below every within-group number. The 0.9796 accuracy is
  computed on 336 predictions out of ~11,000 opportunities. Breadth did not transfer; accuracy did.
* **The target is a syntactic property** (return-shape class). This is exactly the kind of thing syntax can
  predict *by definition*. It is not causal structure, not a state machine, not a bug fix.
* **It says nothing about SWE-bench.** No task was solved, no patch produced, no test suite passed.

So the honest sentence is: *a syntactic vocabulary transfers across codebases without losing accuracy, on a
narrow target, with low coverage, in two groups.* That is a real result and it is a small one.

## 5. What this implies for the prompt's four plays

The prompt's plays 1, 2 and 4 (repo-native component mining, dual-program splicing, cross-modal Petri nets)
all require a **typed symbol space harvested from the repository** — the repository's own functions as
transitions. This round says the *relations* over such a space are portable. It says nothing about whether
the harvesting step works, and the prompt asserts it already does:

| prompt claim | status (audited by tool, `AUDIT_THE_PROMPT_CLAIMS_20261124_V1.json`) |
|---|---|
| `repo_component_and_cow_engine_v1` exists | **failed** — 13 mentions, 0 files |
| `typed_invention_v1.py` exists | **failed** — 3 mentions, 0 files |
| `instant_swe_skill_store_v1.py` exists | **failed** — 13 mentions, 0 files |
| `UnifiedCrossModalPetriNet` exists | **failed** — 13 mentions, 0 files |
| `MealyAPICompiler` exists | **failed** — 2 mentions, 0 files |
| `witness_inversion_v1.py` exists | **verified** — real module, real tests |
| `zygote_worker_pool_v1.py` exists | **verified** — real module |

So Step 1 of the prompt's execution order ("wire it into `witness_inversion_v1.py` / `typed_invention_v1.py`")
has one real target and one that does not exist. And the CoW plays depend on fork-based rollback, which I
measured last round: **fork rolls back the Python heap and nothing else** — filesystem, sqlite and spawned
processes all leak. A patch or a GUI action touches exactly those.

## 6. Verified / unverified / failed

**Verified by execution:** the two-row transfer table; the 1-point accuracy gap; coverage 3.05%; the artifact
carries all four caveats and a test asserts they stay there.

**Failed, mine, prior rounds and now resolved:** un-lifted transfer (V15) and lifted-but-still-grounded
transfer (V16) — both now explained as the same defect with different severity, and the explanation is
measured rather than argued.

**Unverified:** whether syntax transfers when the target is *behavioural* rather than syntactic — for
example whether a return-shape vocabulary predicts which of two functions a failing test exercises. That is
the next honest step and it is much harder.

**Not publishable:** any benchmark row — `docker: command not found`, logged once. Nothing here is a claim
about SWE-bench Pro, Terminal-Bench 4.0, or OSWorld 2.0, and no comparison to any frontier model is made.

## 7. Cost, tests, state

```
model_calls 0 · stored_parameters 0 · network_at_run_time 0 · duration 120.3 s
```

5 new tests on the transfer finding plus 5 existing ones re-run green. Guard PASS (17 rules).

## 8. Next

The gap between this result and anything useful is one specific thing: **syntax predicts syntax, and
nothing here predicts behaviour.** The next instrument must make the target behavioural — take a function
whose *test outcome* is known from this repo's own test suite, strip the test, and ask whether a syntactic +
provenance vocabulary predicts pass/fail. That is the smallest honest step from "the vocabulary transfers"
to "the vocabulary is about something that happens", and it can fail visibly, which is what makes it worth
building.

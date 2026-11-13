# A skill learns WHERE it applies, from executed observations, in five of them

**Date:** 2026-11-12 **Carrier:** Arena session sandbox **Authority:** NONE — producer-run measurement on constructed fixtures
**Modules:** `canonical/swe_kernel/skill_scope_acquisition_v1.py`, `canonical/tools/skill_scope_acquisition_probe_v1.py`, `canonical/tests/test_skill_scope_acquisition_v1.py`
**Reproduce:** `python3 canonical/tools/skill_scope_acquisition_probe_v1.py` · `python3 -m pytest canonical/tests/test_skill_scope_acquisition_v1.py` (21 tests)

## The claim, bounded

One crystallized boundary lesson, run against eight victims each executed against **its own** specification, buys its condition of applicability in **5 observations**: `required = ('baseline.violates_own_spec',)`, status `IDENTIFIED__ONE_CONSISTENT_REQUIREMENT`, **1** survivor. Enforcing that scope takes breakages of already-correct code from **3 → 0** while repairs stay **5 → 5**, through refusals issued *before* any edit.

That is the whole claim. It is not that skills now generalize, and not that the shipped corpus has scopes — see the last section.

## Why this was missing

The law and the instrument already existed and had nothing to read:

- `canonical/runtime/applicability_v1.learn(evidence)` identifies the requirement a set of observations supports, and refuses with a named reason when they do not. It needs `Sequence[(state, succeeded)]`.
- `canonical/runtime/contrast_selection_v1.select_contrast(evidence, pool)` names the observation that splits the surviving requirements most evenly. The caller owns realisability.

Measured on the shipped records: skills carry `provenance {at, hits, origin}` and `verified_hits` — **counts**. `crystallize_code_fix` does store `training_baseline` (returncode 1, test_count 2) and `training_verification` (returncode 0), a real failure and a real success, but in a shape the law cannot read. Hence the scope ledger reporting 5 of 5 skills `EXACT_MATCH_ONLY`. And a grep across `canonical/` for `facts_of|state_of|observable_facts|extract_facts|observe_state` returns **nothing**: no module in the tree turned a source text into observable facts at all.

`rule_scope_learning_v1.learn_scope` is adjacent and is not this. It narrows among three hypothesis *levels* — `SCOPE_STATEMENT`, `SCOPE_OPERATOR`, `SCOPE_SEMANTIC` — i.e. which rewriting machinery a lesson needs, and returns `{"scope": hypothesis_id}`. It never calls `applicability_v1` or `contrast_selection_v1`. Choosing the mechanism and identifying the domain are different questions.

## The measurement

The lesson is taught through the production store (`VerifiedSkillStore.crystallize_code_fix`, `x <= hi` → `x < hi`, twin oracle name-agnostic). Its derived swap family is `[('<=','<'), ('>=','>'), ('>','>=')]` — which is precisely why it fires on already-correct inclusive code: `>=` → `>` ruins it. This is the defect `skill_precondition_presence_v1` recorded, now reproduced as a boundary.

| | fired | repaired | **broke correct code** | not applicable |
|---|---|---|---|---|
| without a scope | 8 of 8 | 5 | **3** | 0 |
| with the bought scope | 8 of 8 | 5 | **0** | 0 (3 refused before editing) |

The dose-response ladder — the part that answers *"is one try enough?"* with a number instead of an adjective:

| observations | status | required |
|---|---|---|
| 1, 2, 3 (successes) | `UNDETERMINED__NO_CONTRASTING_OUTCOME` | `None` |
| 4 (first failure) | `AMBIGUOUS__SEVERAL_CONSISTENT_REQUIREMENTS` | `None` |
| **5** | **`IDENTIFIED__ONE_CONSISTENT_REQUIREMENT`** | **`('baseline.violates_own_spec',)`** |

Three successes bought nothing. The first failure changed the answer, and one more observation closed it.

Each refusal names what it prevented, not merely that it declined: `return_site_already_correct`, `if_guard_already_correct`, `flipped_operands_already_correct` — all three `missing=['baseline.violates_own_spec']`, all three `would_have_been=BROKE_CORRECT_CODE`.

## Two-sided controls

- **Earnability.** Delete the failures and the same code returns `UNDETERMINED__NO_CONTRASTING_OUTCOME`, reason `NO_FAILURE__NECESSITY_IS_ONLY_REFUTED_BY_FAILURE`, `required=None`. If the label were reachable from successes alone it would be a constant, not a measurement. This is the same control that measured `0 of 200` requirements identified from one success in `contrast_selection_v1`.
- **Realisability.** Offered only the states already observed, `select_contrast` returns `NO_REACHABLE_STATE_SPLITS_THE_SURVIVORS` — it does not invent an experiment. Offered the states the *remaining* victims would actually produce (computed by executing their specs), it returns `SELECTED`, informative, survivors 2 → 1, with the discriminating fact named. Once the boundary is bought it returns `ALREADY_IDENTIFIED__NO_CONTRAST_NEEDED` rather than manufacturing work.
- **Mutation.** 18 of 18 mutants killed, 0 survived. Two initially survived and both were the same defect in my own test suite rather than in the module: `while_guard_needs_only_an_ancestor` (no case where a `while` merely *contains* the comparison) and `buy_scope_reports_no_non_firings` (a reported count nothing pinned). Both are now pinned.

## Three traps this was built out of, each hit for real

**1. A victim the skill never fires on is NOT a failure.** It is `NOT_APPLICABLE` and yields no observation, because nothing was tried and nothing was learned. Counting a non-firing as a failure builds a boundary out of the *tokenizer's* reach instead of the skill's domain — the same error as counting a `PASS` that only proved a process started. Every row therefore carries the verdict that produced it, and firing is a precondition for being evidence. A non-firing still **costs** an observation, and that cost is reported rather than hidden.

**2. A substring is not an observation.** The prototype used `"return " in source` for `site.return`, which is true of a function whose return is nowhere near the operator. On that crude fact the law identified `{baseline.violates_own_spec, site.return}` — plausible, wrong, and *narrower* than the truth. On the AST the same evidence yields `{baseline.violates_own_spec}` alone. A crude extractor does not fail loudly; it reports a scope that looks identified. Likewise an `if` or `while` that merely *contains* the comparison is not a guard on it, which is why the site facts are computed by testing whether the node is the enclosing statement's `test`.

**3. An unexecuted baseline is not a fact.** With no specification executed, `observable_facts` emits `baseline.not_executed` and no baseline fact at all. And for a language with no extractor it raises `NO_FACT_EXTRACTOR_FOR_LANGUAGE:go` rather than running a Python walker over Go source, because a fact computed by the wrong parser is worse than no fact.

## What this does NOT say

- **That the acquired condition is TRUE in general.** It is the one requirement consistent with the observations made. `learn` says so itself: with successes only it refuses, and with several consistent requirements it returns `AMBIGUOUS` rather than picking one.
- **That the shipped corpus now has scopes.** It does not. Acquiring one needs victims and a specification for each, and neither is stored with a skill. Five shipped skills remain `EXACT_MATCH_ONLY`. This gap is named, not papered over.
- **That `admits` accepts anything.** It decides whether a skill may be **proposed** against a target. The caller's verifier still decides the outcome, and the module exposes no `apply`, `accept`, `commit`, `store` or `save` surface — pinned by a test.
- **That a fact absent from a state was observed false.** Absent means not observed true.
- **That this is model training.** It is not, and nothing here needs it to be. See below.

## Relation to the four requirements in the critique

The critique said real generalization needs (1) actual model training, (2) conceptual understanding rather than string matching, (3) transfer across unrelated domains, (4) reasoning about why a solution works. What this round establishes is narrower and executable:

- **(2) is partly answered, and the answer is a mechanism, not a promise.** The scope is now expressed over computed facts about a target's own behaviour against its own specification — `baseline.violates_own_spec`, `site.if_guard`, `operator.GtE` — not over token overlap. That the difference matters is not asserted; it is measured: the substring version of the same vocabulary produced a wrong scope from the same evidence.
- **(4) is answered for one question only.** "Why does this skill work here?" now has an answer the tree can compute and a refusal when it cannot. Why the *fix* is right remains the oracle's business and is unchanged.
- **(1) is not needed for this, and the evidence against needing it is not mine.** SkillOpt (Microsoft Research, 2026-05-25) trains the skill document as the external state of a **frozen** agent — bounded add/delete/replace edits accepted only on strict held-out improvement, zero inference-time model calls, **no weight updates** — and was best or tied-best on **52 of 52** (model, benchmark, harness) cells against no-skill, human-skill, one-shot LLM skill, TextGrad, GEPA, Trace2Skill and EvoSkill. Conversely Skill-V (2026-10-08) ablated the gate itself: Static Library 73.40, Acquisition Only 68.80, Failure-only 67.20, Full 95.30 — accumulating experience *without* a falsifiability and revision gate is **worse than not learning at all**. SkillCommit (2026-08-15) is the direct refutation of similarity-based generalization: merging by semantic similarity or LLM judgment "may merge superficially related but behaviorally incompatible strategies". This tree's `semantic_generalization_engine_v1.py` is exactly that, and a grep for `oracle|verify|refuse|wrong|expect|assert|falsify|contradict` in it returns **0**.
- **(3) is untouched.** Cross-domain transfer was not attempted and no claim is made about it. The only cross-language work in the tree is Round E's `operator_semantics_v1`, where `%` and `/` were **refuted by witnessed counterexample** (python3 `-7 % 3` = 2, node = −1; `7 / 2` = 3.5 vs 3), and `SAME` means only a failure to refute on one probe.

## Verdict on "do it once ⇒ learned forever"

Not as stated, and this round is the reason the distinction is now measurable rather than rhetorical. One demonstration buys **history**. A boundary costs **five observations, one of which must be a failure**, and it buys a condition that is true of the observations made and unknown beyond them. Three successes in a row bought nothing at all — the tree refused to name a requirement, which is the correct behaviour and the opposite of "instant".

"One try is enough exactly when the interface and the verifier already do the generalising." That sentence survives this round unchanged. What is new is that when one try is *not* enough, the tree can now say how many were, what they bought, and what it still cannot tell.

# A real repair is a whole file. A lesson is one statement.

**Date:** 2026-11-12 **Carrier:** Arena session sandbox **Authority:** NONE — producer-run measurement in one sandbox, not independent verification
**Modules:** `canonical/swe_kernel/lesson_localization_v1.py`, `canonical/tools/real_repair_localization_probe_v1.py`, `canonical/tests/test_lesson_localization_v1.py`; site-relative facts added to `canonical/swe_kernel/skill_scope_acquisition_v1.py`
**Reproduce:** `python3 canonical/tools/real_repair_localization_probe_v1.py` · `python3 -m pytest canonical/tests/test_lesson_localization_v1.py` (24 tests)

## The owner's question, answered with an execution

*"Why can't we just give our model the most advanced coding actions and let him experience them once and then he will learn them? Can't we do this now?"*

It can be done now, on real third-party code, and this round did it. But the tree's own teaching path could not, and the reason is mechanical rather than conceptual:

**Teaching a real repair the way the tree teaches it produces a permanent no-op.** Given the two whole 1317-line files of the pinned boltons `bytes2human` boundary fix — exactly what the curriculum worker passes as `before_snippet` and `after_snippet` — anti-unification yields **13 holes over 99 vs 99 tokens**. `derive_operator_swap` then returns `None`, *correctly*: it requires the two token streams to differ at exactly one operator position, and this pair differs in a docstring as well as the operator. The rule is stored, marked `state=ACTIVE`, and proposes **0 candidates on all four real corpus sources**.

`error_class` is not the cause — `GENERIC` and `BOUNDARY` produce byte-identical token streams, which is pinned by a test.

So one real experience, taught the way the tree teaches, currently buys a skill that fires nowhere and nothing notices, because no gate asks *"does this skill fire at all?"*

## What localization buys, executed

`lesson_localization_v1` finds the smallest **statement** covering each changed region. On the same real repair that is

```
if abs_bytes <= next_size:      ->      if abs_bytes < next_size:
```

which derives `<=` → `<` with family `[('<=','<'), ('>=','>'), ('>','>=')]`, and **survives the production store** (`VerifiedSkillStore.crystallize_code_fix` → `crystallized=True`, swap intact after storage). Statement granularity is what makes one real repair into one lesson: the enclosing *function* carries two differences and is refused.

Each real target was then judged by **its own upstream test body**, unmodified, through `ProjectTestOracle` (which copies the project, writes the candidate, runs the suite, and never patches the original). Budget: 12 candidates executed per target, stated in every verdict that depends on it.

| real case | baseline vs its own tests | candidates | verdict |
|---|---|---|---|
| `unit_boundary` — boltons/strutils.py | rc=1, **4 tests** | 9 tried / 9 | **REPAIRED** (candidate 1) |
| **`bits_capacity` — boltons/mathutils.py** | rc=1, **3 tests** | 4 tried / 4 | **REPAIRED** (candidate 2) |
| `ichunked_zero` — more_itertools/more.py | rc=1, **10 tests** | 12 tried / 32 | **FIRED_AND_NOT_REPAIRED_WITHIN_BUDGET** |
| `chunked_even_zero` — more_itertools/more.py | rc=1, **12 tests** | 12 tried / 32 | **FIRED_AND_NOT_REPAIRED_WITHIN_BUDGET** |

**The headline is `bits_capacity`.** A lesson localized from a bug in `boltons/strutils.py::bytes2human` was applied to a *different module*, `boltons/mathutils.py::Bits.__init__`, whose real historical fix is `if val > 2 ** len_:` → `>=` — the dual form of the taught swap, reached through the swap family rather than by being told. Candidate **2 of 4** is **byte-identical to the sha256-pinned upstream `after.py`**, and it **passes that module's own 3 upstream tests** while the baseline fails them.

That is one experience, learned once, repairing a real bug it was never shown, verified by the injured project's own tests.

## The two failures are real and are reported as failures

The more-itertools bugs are **missing zero-guards**, not operator boundaries. Localization refuses them by name (`NO_OPERATOR_LESSON__NO_REGION_IS_A_SINGLE_OPERATOR_DIFFERENCE`) rather than manufacturing an operator rule — which matters, because such a rule fires **56 times** on `more.py` and repairs nothing.

The skill still fires on them (32 candidates each) and does not repair within budget. That is recorded as `FIRED_AND_NOT_REPAIRED_WITHIN_BUDGET` **with the budget stated**, never as a pass and never as a non-firing. A corpus control is pinned alongside: each case's real upstream fix *does* pass its own tests, so these failures belong to the skill and not to a broken harness.

## A trap that was live, and is now pinned

With `pytest` absent from the sandbox, `bits_capacity`'s upstream test failed at `from pytest import raises`, the oracle reported `test_count=0`, and **even the sha256-pinned upstream fix returned non-zero**. Counting that as a failure of the skill would have fabricated a contrasting observation out of a missing dependency — the same error class as counting a `PASS` that only proved a process started. Zero tests run is now `UNVERIFIABLE__ITS_OWN_TESTS_DID_NOT_RUN` and yields no observation, pinned by a stub-oracle test. This matches the tree's existing convention: `TOOLCHAIN_ABSENT__NOT_A_PASS`.

## The scope law on real code: an honest negative

Round F identified `required = ('baseline.violates_own_spec',)` from five executed observations on constructed fixtures. On this real corpus it **cannot**, and the reason is instructive:

- **All four real targets already fail their own tests.** So `baseline.violates_own_spec` is present in every observation and refuted by none. `constant_facts` reports it — together with `operator.Gt` — as constant across the corpus. A fact true of everything is not a requirement; it is the corpus saying nothing.
- **Whole-file facts are degenerate on real modules.** `before.py` and its own `after.py` — which differ by the actual historical fix — produce **identical 26-fact sets** (sites `{assignment, if_guard}`, all nine comparison operators). A vocabulary that cannot tell a defect from its own repair cannot scope anything.
- **Site-relative facts** (computed at the offsets where the skill actually fires, reconstructed with the proposer's own scanner) cut the law's survivors from **1024 → 0** on the same evidence, and change the verdict from `AMBIGUOUS__SEVERAL_CONSISTENT_REQUIREMENTS` to `INCONSISTENT__NO_REQUIREMENT_EXPLAINS_THE_EVIDENCE`.

`INCONSISTENT` is the more useful refusal and it is pinned rather than dressed up. It says the **vocabulary** is wrong, not that the evidence is thin: the two failures' site-fact sets (45 facts each) are **supersets** of the two successes' (10 and 7), so no conjunction of *present* facts can separate them. The property that actually discriminates — *the defect is an operator boundary rather than a missing guard* — is not expressible as "these facts hold". Two consequences follow, both named:

1. Facts must be able to express **absence**, or the unit of observation must become `(target, site)` rather than `target`.
2. Even site-relative facts **blur**: they are a union over all 9 firing sites, so `operator.LtE` is present in both `before.py` and `after.py`. What actually disappears is the defect site's own operand (`left_operand.name.abs_bytes`). That is pinned too.

## What this does NOT claim

- **Not that the localized lesson is the right lesson for the corpus.** It repaired 2 of 4 real bugs and failed on 2. It is one operator difference at a located statement, which `derive_operator_swap` checks token by token.
- **Not that `crystallize_code_fix` now localizes.** It does not, and this round deliberately did not edit it: teaching a localized pair while verifying a whole file would break its downstream reproduction checks (`verify_rule_on_mutated_twin`, `iter_crystallized_code_rule_candidates`), which assume the rule reproduces `after_snippet` from `before_snippet`. Making those region-relative is the named next step, not something to half-apply.
- **Not that the shipped corpus has scopes.** It still does not; the ledger is unchanged at 5 of 5 `EXACT_MATCH_ONLY`.
- **Not that the scope law now works on real code.** It returns `INCONSISTENT` here, and that is the finding.
- **Not a benchmark result, and not model training.** No model was called; every verdict is an executed test suite over pinned real sources.
- **Not that the fixtures are independently certified.** `PROVENANCE.json` states `independent_certification: false` and `full_upstream_repository_coverage: false`; sources and upstream test snapshots are unmodified and no network is required at test time.

## What the 2026 literature says, and where this sits

- **SkillsBench** (arxiv 2602.12670): curated skills +16.2 pp, but **self-generated skills −1.3 pp**, and **16 of 84 tasks show negative deltas**; the stated common cause is "a single 'correct' pipeline **without applicability boundaries** or lightweight fallbacks", and the implication drawn is that *"Skills should include applicability boundaries, not just preferred procedures."* That is precisely the gap measured here.
- **SoK: Agentic Skills** (2602.20867): formalizes an applicability condition *C* — "a skill should activate only when its procedural knowledge is beneficial" — and documents the ClawHavoc supply-chain case where ~1,200 malicious skills used **overbroad descriptions** to activate across broad task categories. Over-broad applicability is a security surface, not only an accuracy one.
- **A-CEGIS** (2609.02892): counterexamples as feedback, with negatives generated from positive seeds by *small edit operations* against a deterministic oracle, and a hardening pass that searches a probe pool for witnesses where gold and candidate disagree. Localization is the same move at the level of the lesson rather than the candidate.
- **SkillEvolver** (2605.10500), case `court-form-filling`: a distilled heuristic "true for medical intake and false for legal forms", where **refinement re-explored the same training data and baked the heuristic deeper**. This is the argument against synthesizing contrasts only near the original demonstration, and for a corpus of *other* real targets — which is what the pinned fixtures provide.
- **When Skills Don't Help** (2605.20023): names **false lesson propagation** — "the agent encodes a spurious causal lesson from a small number of prior trajectories and applies it in an inappropriate context" — and identifies *environment-feedback bandwidth* as the missing variable. An inert rule that fires nowhere is the degenerate case of the same failure.
- **SWE-Skills-Bench** (2603.15401): **39 of 49 skills produce ΔP = 0**, average +1.2%, with near-match templates causing *surface anchoring* and *concept bleed*. A skill that proposes 0 candidates is ΔP = 0 by construction.

The mechanism is therefore not novel in conception — the frontier converged on falsifiable applicability conditions — but the specific defect it removes (whole-file teaching yielding an inert rule) and the specific evidence (a lesson transferring to a different real module's pinned upstream fix) are measured here rather than asserted.

## Verification

- `canonical/tests/test_lesson_localization_v1.py` — **24 passed**, running the real pinned fixtures and the real upstream test suites
- `canonical/tests/test_skill_scope_acquisition_v1.py` — **21 passed**, unchanged, after the site-relative addition
- Fifteen-suite batch (Rounds E and F plus applicability, contrast, ledger, precondition, rule-scope-learning, `what_a_success_teaches`) — **238 passed, 0 failed**
- Post-merge re-run — **45 passed**, probe reproduces every number
- Mutations — **16 of 16 killed, 0 survived**, across all three files
- `canonical/verification/REAL_REPAIR_LOCALIZATION_20261112_V1.json` records the measurement itself — both arms, every transfer verdict with its test counts, the fact-vocabulary numbers, the pinned trap and the sources — with `authority: NONE__PRODUCER_RUN_MEASUREMENT_IN_ONE_SANDBOX_NOT_INDEPENDENT_VERIFICATION`
- Declaration floor: `HELD: declaring_none 595 == floor 595`; the new JSON adds **0**. Reproduce with `python3 canonical/tools/auditability_report_v1.py --floor --baseline canonical/verification/AUDITABILITY_DECLARATION_FLOOR_20261112_V1.json`. The floor is not moved by this round and does not record its own numbers — a floor that recorded this round's output could not fail it
- Unified-model artifact: recompiled **last**, after this document, the verification JSON and the action intent were final. `verify_brain_unified_model_v1.py` reports `TOTAL 33/33 PASS`, `MODEL_DEPENDENCE_AUDIT 4/4 PASS`, `AUTHORITY NONE`, and the digest it prints is the one CI checks. The artifact is content-addressed over `canonical/verification/`, `canonical/action_intents/` and the root claim documents, so the digest is deliberately **not** written into any of them — a document that recorded the digest of the artifact that hashes it could never be consistent
- Both governance enforcers were reproduced locally from their copies on the PR base commit, as both workflows run them

## Verdict on "experience it once ⇒ learned permanently"

Closer than last round, and now demonstrated on real code rather than fixtures: one real experience, localized to the statement that changed, produced a stored rule that repaired a *different* real module's historical bug and was verified by that module's own tests. That is a permanent, transferable, executed result.

But three things are still not true, and each is measured rather than argued. **One success still teaches nothing about scope** — `what_a_success_teaches_20261112` measures **0 of 200** cases identified by one success, against **25 of 25** in a mean of **2.76** demonstrations once outcomes include failures, and the tree's own store records **3 successes / 0 failures**. **The scope law cannot yet express what discriminates on real code** — `INCONSISTENT`, because failures' facts are supersets of successes'. And **the corpus still has no scopes**. "Do it once and it is learned forever" holds for the *repair*, and does not yet hold for the *boundary*.

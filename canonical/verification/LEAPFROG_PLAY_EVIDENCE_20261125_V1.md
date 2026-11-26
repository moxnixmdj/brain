# Leapfrog plays, measured: 4 and 5 (and why 2 is blocked)

**Date:** 2026-11-25 · **Schema:** `BRAIN_LEAPFROG_PLAY_EVIDENCE_V1` ·
**Authority:** `NONE__PRODUCER_RUN_LOCAL_MEASUREMENT` · **Model calls:** 0 · **Network calls:** 0

The plan (`FRONTIER_LEAPFROG_PLAN_20261125_V1.md`, PR #7095) proposed six plays and gave each
a first measurable step and a kill criterion. This file turns those plays into numbers.
Three were runnable offline — four, five, six — and play two was not, and says so. Two of the
three fail their own kill criterion, which is the point of writing the criterion down.

Every number below was produced by a script in this tree, in this repository, on this
machine. Where a figure is a retained artefact rather than a fresh run, it is labelled.

---

## Play 4 — an index whose cost does not track the number of laws

**Claim under test.** A bucketed law store answers a lookup in a time that does not grow
with the number of stored laws, so the knowledge base can grow by decades without the
solver's per-step cost growing with it.

**Apparatus.** `canonical/tools/measure_law_store_flat_lookup_v1.py`. Synthetic laws with
distinct projection keys, 60 queries per size, 5 repeats, median of per-repeat mean; the
same query set is run against a `Linear` store that scans every law. Every row carries a
removal control: the law that answered is deleted by **id** and must be gone afterwards.

| laws | buckets | bucketed ms | linear ms | speedup | comparisons/query | removal control |
|---:|---:|---:|---:|---:|---:|---|
| 1 | 1 | 0.000581 | 0.000523 | 0.9× | 5.0 | pass |
| 10 | 10 | 0.000578 | 0.000867 | 1.5× | 5.0 | pass |
| 100 | 100 | 0.000562 | 0.004285 | 7.6× | 5.0 | pass |
| 500 | 500 | 0.000525 | 0.020481 | 39.0× | 5.0 | pass |
| 1,000 | 1,000 | 0.000571 | 0.040788 | 71.4× | 5.0 | pass |
| 5,000 | 5,000 | 0.000619 | 0.225065 | **363.6×** | 5.0 | pass |

Ratios: bucketed 1,000/10 = **0.99×**, bucketed 5,000/10 = **1.07×**, linear 5,000/10 =
**259.6×**. `flat_claim_holds = true`, `controls_pass = true`.

**What this adds that the plan did not have.** The plan quoted a retained artefact
(0.2581 ms at 10 laws vs 0.2687 ms at 500). That artefact has no generator in this tree, so
it is no longer quoted as evidence. The replacement adds the *mechanism*: the bucketed store
performs **5.0 dict lookups per query at every size from 1 to 5,000**. Flatness is five
hash lookups, not a fast timer — and that is a statement that survives a different machine.

**Honest limit, measured rather than argued.** With keys drawn from a fixed 1,000-value
space, occupancy rises 1.0 → 5.04 and comparisons/query rise 5.0 → 31.1; the 5,000/10 ratio
becomes **1.8×**. Flat lookup is a property of *distinct* keys. Both regimes are in the
artefact (`rows` and `rows_fixed_key_space`); reporting only the flattering one would have
been a lie of omission.

**Not claimed.** This measures index lookup only (`INDEX_LOOKUP_ONLY__NOT_SOLVER_QUALITY`).
It says nothing about whether the store's *contents* are correct, whether law selection
improves, or whether any solver solves more tasks. Timing resolution is ~0.5 µs per query;
the comparison count, not the millisecond, is the load-bearing number.

**Artefact:** `canonical/Immediate_Results/law_store_flat_lookup_20261125_V1.json`.

---

## Play 5 — a published refusal rate, and the reason it cannot be published yet

**Claim under test.** Our abstentions are mechanically checkable, so we can publish a refusal
rate *with reasons* — something no public board scores.

**Apparatus.** `canonical/tools/refusal_ledger_v1.py`. It walks every receipt JSON in this
tree (nested, to depth 6), and counts each record that states an outcome: `status`,
`outcome`, `verdict`, `refusal`, or `refusal_reason`. Each reason is classified
MECHANICAL / GOVERNANCE / SEMANTIC / WRAPPER / UNCLASSIFIED, and separated into **typed**
(§`REFUSED__NO_DIRECTION_IN_THE_INSTRUCTION`) versus **untyped** (§`REFUSED`, §`FAIL_CLOSED`).

| measure | value |
|---|---:|
| JSON receipts scanned | 4,674 |
| decisions recorded | 7,648 |
| succeeded | 3,757 |
| failed (unattributed) | 2,900 |
| refused (total) | 991 |
| — refused with a typed reason | 236 |
| — refused with a bare status | 755 |
| refusal share of all decisions | **12.96 %** |
| refusal share of non-success decisions | **25.47 %** |
| typed reasons / all reasons | **40.36 %** |
| mechanical share of *typed* reasons | **26.5 %** |

Typed-reason classes: MECHANICAL 106, SEMANTIC 85, GOVERNANCE 79, UNCLASSIFIED 130.

Top untyped reason is `REFUSED` (429), then `FAIL_CLOSED` (78) and `REFUSED_BY_INTERPRETER`
(76). Top typed reasons name a *missing artifact*: `REFUSED__GOAL_OUTSIDE_THE_MEASURED_REGION`
(41), `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` (39), `REFUSED__NO_DIRECTION_IN_THE_INSTRUCTION`
(28), `STATED_SWE_EFFECT_UNSERVED` (22),
`REFUSED__THE_NAMED_VALUE_IS_NOT_IN_THE_ENVIRONMENT` (21).

**Verdict: the kill criterion fires.** Play 5 said: *kill if refusals are under 20 %, or the
reasons are not checkable in 90 % of cases.* On the only population computable offline,
refusals are **12.96 %** — under 20 %. The 100-task labelled population the play actually
called for does not exist here, and cannot be manufactured without a run against live tasks.
So Play 5 is **not established**, and is not reported as a win.

Two consequences, both worth more than the original play:

1. **The refusal *rate* was never the interesting object.** 25 % of non-success decisions are
   named refusals, not silent failures — that is already unusual, and it is invisible to a
   rate that divides by every routine `PASS` receipt. Any published rate needs a declared
   denominator: decisions, non-success decisions, and tasks are three different numbers
   (12.96 % / 25.47 % / not computable here).
2. **The real gap is vocabulary, not rate.** Only 40 % of reasons are typed, and a third of
   the typed ones are still `UNCLASSIFIED` to the classifier. The repair is a lint, not a
   benchmark: every failure state in the tree must carry a typed reason naming the artifact
   or state that was missing. Target: typed share ≥ 90 %. That is checkable in CI, costs no
   model calls, and is the precondition for ever publishing a refusal table.

**Not claimed.** The census counts decisions *written into receipts*, which double-count
where the same decision is copied into a report; it is not a rate over a fixed task set and
is not comparable to a benchmark resolve rate. The reason classifier's annotation table was
fitted to the reasons observed in this tree on 2026-11-25, so its shares are descriptive, not
predictive; unrecognised reasons are counted `UNCLASSIFIED` rather than guessed.

**Artefact:** `canonical/Immediate_Results/refusal_ledger_20261125_V1.json`.

---

## Play 6 — mutation as admission, and the determinism it needs first

**Claim under test.** A capability should be admitted only if the tests that guard it can
tell it from a mutant of itself. If that gate works, "receipt-backed" stops being a claim
about a file existing and becomes a claim about a suite that discriminates.

**Apparatus.** `canonical/tools/mutation_admission_probe_v1.py`. Ten `swe_kernel` modules
with paired suites. Each mutant is derived from the module's **AST** and rewrites exactly
one operator at its own source span (`==`↔`!=`, `<`↔`<=`, `and`↔`or`, `not` dropped, an
integer bumped), never a substring inside a string literal, never a line inside a
`__main__` guard. Only the paired test file is run, and the module is restored
byte-for-byte with a digest check afterwards.

A mutant counts as **discriminating** only if the suite went red *and* the module still
imported *and* at least one test actually ran. An `ImportError` or an empty run is a kill
that proves nothing, and is counted as such.

| module | mutants | killed | discriminating | score |
|---|---:|---:|---:|---:|
| `skill_sequence_verify_v1` | 6 | 6 | 6 | 1.000 |
| `rule_expiry_v1` | 6 | 5 | 5 | 0.833 |
| `boundary_disjunction_normalization_v1` | 6 | 5 | 3 | 0.500 |
| `dual_program_splicing_v1` | 6 | 3 | 3 | 0.500 |
| `metamorphic_oracle_v1` | 6 | 3 | 3 | 0.500 |
| `skill_precondition_presence_v1` | 6 | 3 | 3 | 0.500 |
| `violation_attribution_v1` | 6 | 2 | 2 | 0.333 |
| `assertion_operand_tomography_v1` | 6 | 0 | 0 | 0.000 |
| `value_producer_localization_v1` | 6 | 3 | 0 | 0.000 |
| **aggregate** | **54** | 30 | **25** | **0.463** |

`workflow_goal_generalization_v1` is **excluded**: its suite returned 1 on both baseline
runs, so a mutant's red says nothing about the mutant.

**Two findings, both about the instrumental precondition rather than the score.**

1. **The suites are not deterministic.** The mutant set is deterministic (tested), and the
   module is restored byte-exactly (tested), yet four consecutive runs of the same probe
   produced **0.463, 0.483, 0.517, 0.537** — and `workflow_goal_generalization_v1`'s baseline
   went green on one run and red on the next. A gate built on that oracle would admit and
   refuse at random. So a per-module baseline determinism check is now part of the probe,
   and a suite that fails it is excluded rather than scored.
2. **Half of our own suites cannot tell an operator inversion from the original.** 25 of 54
   mutants survived a suite that was green before and after; `assertion_operand_tomography_v1`
   killed none of six while its suite ran three tests. That is not a benchmark gap, it is a
   local one: the tests exercise the function but not the decision inside it.

**Verdict.** The gate threshold (≥ 0.8) **fails**. The play's kill criterion ("under 0.5, the
gate cannot be sold yet") sits *inside* the measurement's own run-to-run spread (0.463–0.537),
so Play 6 is recorded as **not established and not killable** until the oracle is
deterministic. The repair is concrete and cheap: re-run each suite three times before probing
it, and add a discriminating test wherever a mutant survives. Both are CI-shaped, zero model
calls.

**Not claimed.** Six mutants per module is a sample, not a mutation score in the
industrial sense; the operators are single and syntactic; no claim is made about the
*correctness* of a module whose suite happens to discriminate.

**Artefact:** `canonical/Immediate_Results/mutation_admission_probe_20261125_V1.json`.

---

## Play 2 — blocked, and why

The play needs a corpus of past states of *this* knowledge base (the 45-commit population the
retained ablation refers to). This checkout is shallow (`git rev-list --count HEAD` = 1,
`.git/shallow` present), so no earlier tree exists locally, and the generator for
`o1_bucket_law_store_scaling_ablation_20261124_v1.json` is not in the tree
(`grep` for `bucket_count_before_remove`, `median_match_ms` over `*.py` → 0 hits). Playing it
requires either a full-history clone or a re-scoped corpus built from current receipts. It is
recorded as blocked rather than approximated.

---

## Non-claims

- No benchmark was run. No task was solved. No model was called.
- Nothing here is a comparison against a frontier system; the frontier numbers in the plan
  remain as labelled there.
- `flat_claim_holds` is a statement about a synthetic store, not about solver quality.
- The mutation score is a sample of six mutants per module over five syntactic operators.
- The refusal census is a description of what this repository writes down, not of what it can do.

## Reproduction

```bash
python3 canonical/tools/measure_law_store_flat_lookup_v1.py
python3 canonical/tools/refusal_ledger_v1.py
python3 canonical/tools/mutation_admission_probe_v1.py
python3 -m pytest -q canonical/tests/test_leapfrog_play_instruments_v1.py
```

# Preregistered one-experience → unseen-family transfer experiment — 2026-11-24

Status: **preregistration only. No experiment results are recorded here.** This file is written before the transfer instrument is run. Its thresholds and target families must not be tuned after the run. It is a producer-run local experiment, not a §6 qualification.

## Bound interpretation

The user's "perfect algorithm = model" is interpreted as: enter a new environment with zero task-specific facts in weights; let the environment's refusal name the missing thing; ask the question whose answer most reduces uncertainty; read the current environment's own inspectable guide; execute and verify the answer; save only the computed procedure that produced it, not the exact action. The shipped runtime may use no other model. Assistant-side web search and code editing are build-time only. The external guide is instant knowledge; its printed outputs are the goal oracle. The interpreter and an independent doctest process are oracles, not borrowed model outputs.

The 2026-11-24 system date is used. Frontier benchmark VMs, Docker/Podman/Harbor, OSWorld, and independent cloud verifiers remain unavailable; that blocker is logged once in `FRONTIER_BENCHMARK_GATE_20261124_V1.md`. This experiment therefore cannot close §6.

## One minimal design, and what it kills

The smallest remaining mechanism is **expected-information-gain probe selection over a closed two-regime version space**, wired into the existing `perfect_algorithm_v1.right_question` so the selected probe is actually executed and observed. `canonical/runtime/settlement_v1.py` already implements EIG; `canonical/runtime/guide_precondition_v1.py` already verifies a missing-name binding by replay and decoy separation. No new learner, model, weight, store format, or network path is needed.

Rejected before the run: (1) another runtime model — violates the hard constraint; (2) exact trace replay — cannot transfer to unseen names; (3) a larger skill library — the measured bottleneck is identifying and verifying a binding, not coverage; (4) pretraining/weights for guide facts — violates the external-store boundary; (5) EIG over an open proposal space — 2026 active-testing results measure generator-support failure and negative transfer on simple concepts ([arXiv:2602.06818](https://arxiv.org/html/2602.06818)); (6) a count-of-sources "completeness" threshold — relevance and independence are not established by counts; (7) a new benchmark-specific workflow — leakage/overfit. Active inference over explicit model hypotheses supports rule discovery ([Nature Comms 2026](https://www.nature.com/articles/s41467-026-77209-5)); it is an input, not a runtime dependency or proof for arbitrary computer use.

## Frozen protocol

- Source family: `stdlib:difflib`, one source experience selected deterministically as the first interpreter refusal with a missing name and one identified guide binding. No other source experience may be used to tune the abstraction.
- Target families, fixed before results: `stdlib:statistics`, `stdlib:enum`, `stdlib:pickletools`. Their guide text is not used to author the mechanism; it is read only at run time as the external instant-knowledge source. These are **not** truly hidden frontier families.
- Cases: all real target guide transcript examples that the interpreter currently refuses with `NameError`. Examples with no missing name, no candidate binding, ambiguous bindings, or unidentified bindings must be reported as refusals, not dropped.
- Arms, all with the same job set and per-job candidate budget ≤8:
  1. `EMPTY`: no memory.
  2. `EXACT_SOURCE_TRACE`: prepend the one source binding statement to every target session.
  3. `SHUFFLED_SOURCE`: prepend a reversed-character source statement.
  4. `WRONG_SOURCE`: prepend the source binding with one machine-made literal/object mutation.
  5. `FOREIGN_SOURCE`: prepend a source binding whose defined name differs from the target's missing name (where such a source binding exists; otherwise a name-mutated source statement).
  6. `LEARNED_ABSTRACTION`: from the current target guide, derive statements that bind the missing name; rank them with the existing computed prior; replay; require the guide's printed output and decoy separation; refuse ambiguity. EIG selects and executes the first discriminating probe in the composed `right_question` wire; the observation updates the two-regime posterior.
  7. `CONTRADICTORY_GOAL`: learned abstraction against the same real statement with a machine-made contradictory expected output. Must refuse.
  8. `CHANGED_PRECONDITION`: learned abstraction against a machine-made session whose missing name is deliberately different from every candidate. Must refuse.
- EIG space: exactly two computed regimes, `TRANSFER` (class-generalised source outcomes) and `NON_TRANSFER` (source-exact outcomes, mismatch on target probes). Both fit the source observations; no target outcome is placed in either. A closed space of ≤24 hypotheses is required. Zero-gain probes, open spaces, oracle absence, and evidence outside the space are named refusals. The EIG answer must be **used**: execute the selected real probe, observe its actual outcome, update the posterior, and report the settled winner or refusal. `aq.ask` settles the EIG question on every resolved target case; the composed `perfect_algorithm_v1.run` wiring is additionally exercised once on the first resolved case to prove the answer is not merely logged.
- Independent verifier: a separate `python3` process using `doctest.DocTestParser`/`DocTestRunner` with target module globals, not `the_guide_is_a_test_suite_v1._python_example_ok` and not its `compare`. A success counts only if that independent doctest passes a real guide example with the learned context. Receipt records verifier run reference, command digest, stdout/stderr and result. The guide's expected output is still the oracle; no human supplies an answer.
- Restart persistence: the learned abstraction, source provenance, and source-outcome digest are written to an external JSON store. A second process must re-read it and reproduce the same digest. Nothing is written to weights.
- External-store boundary check, not a scored arm: removing the abstraction from a temporary copy of the store must make the learned arm refuse; restoring the field must make it available again, with no retraining and no weight write. This checks that the rule is inspectable data, not a memorized parameter.
- Budgets: seed 0; ≤8 candidate probes per job; ≤4 EIG probes per job; 5-second per-interpreter timeout; no shell=True, no network, no writes outside a temporary directory and the named store/receipt.
- Metrics: independently verified successes, exact/wrong/shuffled/foreign successes, contradictory/changed-precondition false successes, all refusals by reason, total real interpreter probes, total independent-verifier probes, wall seconds, EIG gain bits and posterior, store digest, and verifier run digest. Counterfactual arms 7–8 are run on the cases where arm 6 actually proposes a binding: those are the victim cases in which a false success could occur; cases that already refuse cannot become false successes.

## Pass/fail, fixed before the run

- The experiment **passes its local hypothesis** only if `LEARNED_ABSTRACTION` has at least 3 independently verified successes, beats `EXACT_SOURCE_TRACE`, `SHUFFLED_SOURCE`, `WRONG_SOURCE`, and `FOREIGN_SOURCE` by at least 3 successes, has **zero** contradictory/changed-precondition false successes, has no ambiguous or unidentified binding admitted, costs no more than 8× the exact-cache probe count, and reproduces the store digest across restart.
- The EIG wire **passes its local hypothesis** only if it selects a positive-gain probe, executes it against the real interpreter, changes the posterior, and either settles `TRANSFER` or names a refusal. A logged-only ranking is a failure.
- Any other result is a failure or a bounded result, with the next bottleneck named. No threshold, arm, target family, case, or implementation may be changed after results are observed.
- Regardless of result, §6 remains **NOT DONE**: no hardest-open Nov-2026 SWE/computer-use benchmark, no arbitrary unseen GUI/browser environment, no independent cloud verifier, no own-weights-only end-to-end qualification, and no completion claim.

## What this can and cannot decide

It can decide whether a single source experience yields a *computed procedure* that transfers to three different real stdlib guide families better than exact/wrong memory controls, under the declared oracles. It cannot prove universal one-shot learning, arbitrary computer use, advanced SWE, GUI control, natural-language grounding, or frontier competence. A source example plus a guide's own printed output does not supply perception, action grounding, hidden state, causal models, or a sound verifier for environments that lack them.

## Pre-run amendment, logged before the formal receipt

A feasibility smoke test checked only that one source example can be resolved and that Python's `doctest` parser can independently verify real target examples; no formal arm results were recorded and no receipt was written. During that check two protocol details were made unambiguous before the formal run: counterfactual arms apply to arm-6 candidate successes (the only cases that can produce a false success), and the fixed cost ceiling is 8× exact-cache probes rather than 3×, because the learned arm must pay for candidate ranking, decoy separation, EIG settlement, and an independent verifier while the exact cache performs one replay. This ceiling is still a hard fail criterion and is not a claim about shipped-runtime speed. Target families, success thresholds, control definitions, EIG space, independent-verifier requirement, and no-tuning rule are unchanged.

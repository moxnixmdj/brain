# Code-repair mechanism promotion: SyGuS synthesizer in, angelic engine assessed

**Date:** 2026-11-25. **Authority:** NONE (producer-run sandbox).
Follow-up to `PLAN_V2_EXECUTION_STATUS_20261125_V1.md`, which falsified the "compete on proof" plan
and named the next honest move: find a mechanism in the branch-only modules that actually touches
code repair. **Found two. Promoted one. Assessed the other.**

---

## Promoted: `oe_sygus_synthesizer_v1` — verified, self-contained, at the unified runtime

From branch `arena/b81b2217-brain` (HARD-51) @ `4fc832f2`. Now at
`canonical/runtime/oe_sygus_synthesizer_v1.py` (1,118 lines) with
`canonical/tests/test_oe_sygus_synthesizer_v1.py` (3 tests, all passing).

- **Self-contained:** imports only the standard library (`hashlib`, `math`, `re`, `dataclasses`,
  `typing`). No branch-only dependencies.
- **Verified working** (ran it, did not just read it):
  - `synthesize_separating_predicates` finds the semantic guard separating failing from passing
    inputs across Python / JS / C — e.g. `isinstance(size, int) or size < 0`,
    `!Number.isInteger(size) || size < 0`, `floor(size) != size || size < 0`.
  - **Anti-overfit:** it does NOT memorize the failing literals (`0.5`, `-3` absent from output).
  - `test_02` confirms the synthesized predicate actually separates (eval-true on every failing
    input, eval-false on every passing input) — it is a separator, not a guess.
  - `synthesize_value_expressions` reproduces I/O examples exactly.
- **What it is:** bottom-up observational-equivalence (OE) SyGuS enumeration + EUSolver
  information-gain decision-tree predicate synthesis + value/coercion/ITE expression synthesis +
  3-language code emission from one typed AST + Plotkin anti-unification
  (`abstract_synthesized_repair`) for turning a verified patch into an inspectable skill.
- **What it is NOT:** a complete repair loop. It synthesizes expressions and guards from I/O
  examples. It does not localize faults, generate candidate patches, or run a test suite. It is a
  *component* that a repair loop could call. It does not by itself move the reach number.

The branch's full test also exercised UEK/`open_model` integration; that part was not promoted
because `universal_epistemic_kernel_v1` is branch-only. The promoted test covers the core
synthesis, which is the capability.

## Assessed, NOT promoted: `causal_angelic_swe_engine_v1` — real loop, unproven on the corpus

Also from `arena/b81b2217-brain` @ `4fc832f2`. This is the complete repair loop the synthesizer
would plug into:

- **14,164 lines**, plus 5 branch-only dependencies (`instant_swe_skill_store_v1` 1,115,
  `universal_semantic_ir_v1` 1,508, `executable_mental_model_v1` 1,148,
  `repo_component_and_cow_engine_v1` 2,279, `oe_sygus_synthesizer_v1` 1,118) — **~20,300 lines total**.
- **Real techniques:** Ochiai spectrum + traceback causal proximity for localization; counterfactual
  angelic execution (branch flipping, value forcing, statement skipping) for candidate generation;
  live frame separation between failing and passing tests; exception causality; an external
  inspectable skill store that learns alpha-canonical AST skills from verified repairs.
- **113 tests pass** (`CAUSAL_ANGELIC_AND_UNIFIED_CU_BENCHMARK_20261121_V1.json`), claiming repair
  across Python / JS-TS / C++ / C on constructed cases.
- **But:** `authority: NONE`, self-reported, on constructed test cases — **not** on the Part B
  repair corpus (26 tasks, 0 passes) and not on SWE-bench. There is no receipt showing it fixes a
  single real repair-corpus task.

**Verdict: not promoted.** Promoting ~20,300 lines of branch-only code without a single corpus
result would be exactly the mistake this whole exercise is trying to avoid — adding a fixture and
calling it a capability. It is the most promising repair mechanism found, and it is the right
candidate for the *next* step (run it on the Part B corpus), but that step needs the corpus data
(SWE-bench Verified, on HuggingFace, outside this sandbox's allowed hosts) and a decision about
whether a 14k-line monolith is the right vehicle. That decision is not mine to make unilaterally.

## Honest bottom line

- A **verified program-synthesis capability** is now at the unified runtime where it was hidden on
  a branch. That is real, and it is the kind of thing the "hidden capabilities" thesis predicts.
- **Reach is still 0 passes.** The synthesizer is a component, not a loop. The angelic engine is a
  loop, but unproven on the corpus. Neither has been shown to fix a Part B repair task.
- The binding constraint remains what it was: **reach**, and the path through it is still either
  (a) validate the angelic engine on the real corpus, or (b) build the isolation boundary and a
  real repair operator. This turn advanced (a)'s *prerequisite* (a verified synthesis component)
  but did not close the gap.

## What was done

- `canonical/runtime/oe_sygus_synthesizer_v1.py` — promoted from `4fc832f2`, unmodified.
- `canonical/tests/test_oe_sygus_synthesizer_v1.py` — core-synthesis tests (no UEK dependency),
  3 passing.
- This record. No other code edited. The angelic engine was read and assessed, not promoted.

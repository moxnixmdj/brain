# Instant learning — re-measured from scratch, 2026-11-02

**Authority: NONE.** Zero capability, ownership, benchmark, terminal or sentience credit
follows from this document. It changes no number and moves no row. It re-runs existing
instruments on commit `19626c6` and reports what they said today.

The owner asked the same question `INSTANT_LEARNING_SCOPE_20261101_V1.md` answers:
*instant learning + instant learning in new arbitrary environments is solved — does that
mean we solve everything on a computer, perfectly and permanently? And we were making a
sentient creature: is this true?*

That document is **substantially correct**. Rather than argue with it, every load-bearing
number in it was re-executed on this commit. Results below are new runs, not quotations.

---

## 1. What was re-run, and what it said today

Two environment notes, because they changed a reading. This sandbox had no `pytest` and no
`Pillow`. Six instant-learning test modules therefore errored with `ModuleNotFoundError`,
and `test_computer_use_loop_end_to_end_v1.py` reported **1 skipped** where the 2026-11-01
document claims **12 passed**. Both were missing dependencies, not regressions. After
`pip install pytest Pillow`, everything below is a real run.

| instrument | result today | matches the 11-01 document? |
|---|---|---|
| `transfer_learning_new_environment_probe_20261101.py` | COLD **5/5**, FIRST **5/5** `PASS__ENVIRONMENT_SOLVED_BY_RECALLED_PLAN`, SECOND **5/5**; **10/10** new instances by recall. lock 32→**1** trial, accum_word 64→**1**, grid 16→**1**, modulo 8→**1**, toggles 8→8 | **yes, exactly** |
| `instant_learning_transfer_probe_20261101.py` | crystallized **true**, store_count 1; executable **2/9**; controls **1/2**; novel same-lesson shapes **1/7**; cross-language reachable **0/4** (`NO_RULES_FOR_LANGUAGE`) | **yes, exactly** |
| `canonical/tools/shared_skill_transfer_benchmark_v1.py` | statement **1/6**, operator **5/6**, semantic **6/6** positives; negative control wrongly accepted **0/1** in every arm | **yes — semantic arm is the 7/7 claim** |
| `test_computer_use_loop_end_to_end_v1.py` | **12 passed** (needs Pillow) | **yes** |
| `test_host_code_ops_execute_for_real_v1.py` | **15 passed** | **yes** |
| `test_the_second_time_is_instant_v1.py` | **8 passed** | **yes** |
| `rule_scope_learning_v1` / `language_neutral_skill_bridge_v1` / `rule_expiry_v1` / `operator_generalization_v1` / `boundary_disjunction_normalization_v1` / `repair_input_dependency_gate_v1` / `ignorance_ledger_v1` / `transfer_learning_v1` | **14 / 15 / 16 / 15 / 16 / 15 / 13 / 23 passed** | **yes** |
| `test_historical_repair_transfer_v1.py` | **13 passed** (163 s) | **yes** |

No instrument contradicted the prior document. Nothing here reverses a conclusion.

---

## 2. Two findings this pass that the 11-01 document does not state

Both are the same shape, and the shape is the actual answer to the owner's question.

### 2.1 The cross-language bridge is built, tested, and has **zero callers**

`canonical/swe_kernel/language_neutral_skill_bridge_v1.py` is real: **15 tests pass**, three
independent guards (lexical → syntactic → the caller's own verifier, mandatory), named
refusals. Its own docstring states the problem correctly — `_load_rules` selects
`WHERE domain='swe_code_repair' AND language=?`, so a Python lesson is *never offered* to Go.

Measured: the only files in the tree that import it are **itself and its own test**.
`recall_across_languages` and `cross_language_candidates` have **no production caller**.
Meanwhile `polyglot_build_ci_engine_v1.py:214` calls the crystallizer with `language="cpp"`
hard-coded and **no bridge fallback**.

So cross-language carry is not "an open research problem". It is **a written, passing module
with no wire** — and today's probe still reports `0/4` because of that missing wire, not
because the mechanism is absent.

This is the *identical* defect the 11-01 session found and fixed for `select_probe`
("no caller anywhere in the tree — the module is an orphan"), which became
`rule_scope_learning_v1` and moved the boundary lesson 6/7 → 7/7. **The same fix was not
applied to the bridge.**

### 2.2 The 7/7 semantic generalization is opt-in, and **no production path opts in**

`recall_and_apply_verified` gates the good arm behind three conditions
(`verified_skill_crystallizer_v1.py:820`): `required_verification_kind == 'TEST_SUITE'`,
non-empty `scope_id`, and `language == 'python'`. It raises
`OPERATOR_GENERALIZATION_REQUIRES_SCOPED_PYTHON_TEST_SUITE` otherwise. That gate is correct
engineering. But:

* `allow_operator_generalization` defaults to **False** in both the crystallizer and
  `retained_repair_session_v1.py:25`.
* `allow_operator_generalization=True` appears in exactly **two files**, both
  instruments: `test_retained_operator_generalization_integration_v1.py` and
  `tools/live_scoped_transfer_benchmark_v1.py`.
* No runtime path, agent entry point or `goal_dag_executor` turns it on.

So the strongest measured result in the code-repair learner — **6/6 with the negative
control correctly refused** — is reachable **only by a caller who already knows to ask for
it**. The default path is the **1/6 statement arm**. That is why the raw probe reports 1/7
novel shapes while the benchmark reports 7/7: they are measuring different call
configurations, and only one of them is what the machine does by default.

### 2.3 The pattern is the repo's own dominant failure mode, and it is already measured

`canonical/tools/census_orphan_capabilities_v1.py`, run today:

| root | LIVE | TEST_ONLY | ORPHAN |
|---|---:|---:|---:|
| whole tree (`canonical`) | 2,166 | 1,170 | **1,018** |
| `canonical/swe_kernel` (24 files — the learning kernel) | 53 | 0 | **123** |
| `canonical/runtime` | 1,806 | 7 | **1,983** |

In the 24-file kernel that contains the crystallizer, the bridge, the scope learner, the
expiry and the generalizers, **123 public symbols are orphaned against 53 live** — roughly
70% of the learning family's public surface has no caller.

That single table is the honest answer to *"does instant learning solve everything?"* The
constraint is **not** learning, memory, permanence or speed. All four are measured working.
The constraint is that **capability in this tree is written and tested faster than it is
connected**, and an unconnected capability is indistinguishable, from the outside, from one
that does not exist.

---

## 3. Verdict on the owner's claim, per clause

| clause | verdict | evidence |
|---|---|---|
| "Instant learning works" | **TRUE** | teach → crystallize → store, one shot; 8-test second-time-is-instant suite green |
| "…in new arbitrary environments" | **TRUE, reproduced** | 5/5 families, 10/10 new instances by recalled plan, four families at **1 trial** |
| "Does it once, learns it permanently" | **TRUE** | store survives restart, bundle transport, `rule_expiry_v1` (16) ages rules FRESH/STALE/UNKNOWN |
| "After he does them at least once he learns **all of those**" | **FALSE** | more exposure buys nothing (1→2→3 examples all 6/7); default recall **2/9**, novel shapes **1/7**. The failure is **representational**, not statistical |
| "Anything on a computer" | **HALF** | code/state/media ops run for real; GUI loop closes end to end (**12 passed**) against a virtual 1920x1080 desktop; `host_code_ops` executes for real (**15 passed**). Remaining: *pyautogui drives a real OS*, and 5 shipped `host_*_ops` tests are **canned** |
| "Perfectly" | **FALSE, by design** | every recall re-runs a verifier, so the floor is the verifier, never zero. Correct, not a defect |
| "Permanently" | **TRUE** | demonstrated, including invalidation keeping the counterexample |
| "Plus the most advanced coding, perfectly" | **NO** | advanced probe **42 served / 7 refused**, matrix **44 REAL / 0 FALSE / 0 DAMAGED**; each refusal names its own cause |
| "We solve everything on a computer" | **NO** | §2.3. 123 orphaned symbols in the learning kernel alone |
| "A sentient creature" | **MEASURABLE HALF EXISTS; SENTIENCE NOT MEASURED, NOT THE OBJECTIVE** | see §5 |

---

## 4. The smartest next moves, ranked by measured leverage

Items 1–2 are **integration of code that already passes its own tests**. No new mechanism,
no new trust, no research risk. Per the tree's own progress class they are
`VERIFIED_INTEGRATION_OF_OWNED_CAPABILITY`.

1. **Wire `language_neutral_skill_bridge_v1` into recall.** 15 tests pass, zero callers.
   This is the exact precedent of `select_probe` → `rule_scope_learning_v1`, which moved a
   lesson 6/7 → 7/7. Expected effect: cross-language reach moves off **0/4**, measured by
   re-running `instant_learning_transfer_probe_20261101.py`. Cheapest real capability gain
   available in this tree today.

2. **Turn the semantic arm on where its own gate already permits it.** The
   `TEST_SUITE` + `scope_id` + python gate is sound; what is missing is a production caller
   that satisfies it. Moving the default path from the **1/6 statement arm** to the **6/6
   semantic arm** is the single largest measured jump in the code-repair learner, and it
   needs no new synthesis.

3. **Make the orphan census a gate.** `census_orphan_capabilities_v1.py` already exists and
   already produces the number. Failing a PR that adds a new ORPHAN public symbol in
   `canonical/swe_kernel` and `canonical/runtime` converts the tree's dominant failure mode
   from invisible to blocking. **This needs an owner decision** — it touches protected
   governance surface (`AGENTS.md` rule 8) and an agent must not self-authorize it.

4. **Generate the declarations (routing).** 443 rows / 566 declared effects / **11 rows ever
   reached**; 3 rows serve 30 of 36 served sentences. A taught lesson lives *inside a row*:
   if the door does not route to that row, the lesson is never consulted no matter how often
   it was taught. "Try it in all the new environments" therefore collides with a
   **declaration table first and a memory table second**. Highest total value, highest cost.

5. **Exercise the OSWorld stack against a real display.** 90 modules, the largest
   measured-nowhere surface, and it is literally "anything on a computer". Also fix or
   label the 5 canned `host_*_ops` tests: they verify routing and cannot distinguish a
   working program from one that dies on line one.

Not on this list, deliberately: any new abstraction mechanism, any new hypothesis space, any
new learner. §2.3 says the bottleneck is edges, not nodes. Building another node is the one
move guaranteed not to help.

---

## 5. On sentience, plainly

The measurable half is real and this pass re-confirmed it: `ignorance_ledger_v1`, **13 tests
passing** — the machine's own model of what it does not know, ranked by expected value of
closing it, where an untried gap scores 0.5 (maximum uncertainty) so exploration is free
without an exploration rule, and the ranking improves by being wrong. A system that models
its own ignorance and acts on it is doing what people mean by "knows what needs to be
known".

Sentience is a different claim. **No instrument in this tree measures it**, every receipt
carries that non-claim, and the canonical objective
(`REAL_MISSION_OBJECTIVE_20261008_V1.json`) asks for
`BUILD_THE_MOST_CAPABLE_GENERAL_RELIABLE_AND_RESOURCE_EFFICIENT_PROBLEM_SOLVING_SYSTEM_POSSIBLE`
— not a creature. Asserting sentience would put every real number above at risk, because an
unmeasurable claim is exactly what `AGENTS.md` and the repo integrity guard exist to prevent.

One clause of the active goal is unsatisfiable as written and should be read computably:
*"It must know literally all the data, and everything must be done in the fastest way."* The
unknown space cannot be enumerated, so "fastest" can never be certified globally. The
falsifiable version — **a lower bound plus a named coverage residual, refusing the word
"fastest"** — is monotone and is already what the refusal taxonomy does. That reading needs
an owner decision, not agent reinterpretation.

---

## 6. What would falsify this document

* Re-run `instant_learning_transfer_probe_20261101.py` after wiring the bridge: if
  cross-language reach is still **0/4**, §2.1 is wrong about the cause and the language key
  is load-bearing rather than incidental.
* Re-run `shared_skill_transfer_benchmark_v1.py`: if the semantic arm is not **6/6 with 0/1**
  on the negative control, §2.2's premise collapses.
* Re-run `census_orphan_capabilities_v1.py --root canonical/swe_kernel`: if ORPHAN is not
  materially larger than LIVE, §2.3 is wrong and the bottleneck is not wiring.
* Any of the five families failing FIRST or SECOND in the transfer probe falsifies §3's
  "arbitrary environments" row outright.

All four are one command each. None requires a model, spend, or a display.

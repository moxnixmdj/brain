# What is real, what is not, and the smartest next work — 14 November 2026

Authority: **NONE**. This is a producer-run sandbox measurement and repair note on branch
`arena/b8a1050b-brain`, base `fee45dc43f8c145db0776ce8e1f49e1ebf1b78d9`. It registers no capability,
flips no family, updates no weights, and does not edit `truth.achieved`. Independent verification is
still open.

## 1. The claim under test

> “Show it once, it learns permanently; therefore it can solve any computer task and the most
> advanced software engineering.”

The direction is real. The quantifiers are false.

- **Permanence is a property of storage.** A row can survive restart without being correct.
- **Correctness is a property of evidence.** A demonstration buys a hypothesis; admission buys
  permanence only when held-out evidence says the hypothesis repairs something new and breaks
  nothing already correct.
- **“Any computer task” is not a storage claim.** It is an execution-authority, perception,
  state-tracking, verification, and recovery claim. This tree does not have an admitted general
  effect carrier.
- **“Instant” is not a learning claim.** Fast recall is real. Fast *correct* generalization outside
  the demonstrated scope is not established.

The smartest sentence this repository can honestly say today is:

> “I cannot do this yet; here is the precise gap; here is external knowledge about it; here is the
> verified admission gate that must be passed before anything becomes permanent.”

Before this repair, even that sentence was being swallowed.

## 2. What was broken, measured before changing anything

On the live tree, these goals reached the controller’s unconfined documentation-fallback refusal:

- `transcribe the audio in this recording to text`
- `get the writing out of that there pdf thing`
- `Add two numbers in Python`

Before:

```text
solve()          -> FAIL__RAW_GOAL_COMPILATION_GAP, executed=False
solve_or_learn() -> FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT
                    side_effects_may_exist=True
                    learning={attempted, post_refusal_policy_summary, computer_env_status}
                    no ignorance-ledger gap, no JIT knowledge
```

The carrier refusal was correct about the effectful fallback: documentation-mined host Python must
not run without admitted confinement. But the return site also claimed possible side effects when
nothing had run, and it returned before the gap/JIT tail. The loop

```text
“I cannot” -> recorded gap -> retrieved knowledge -> verified, admitted capability
```

was severed before its first read-only step.

A second finding: roughly 366 lines after that unconditional return were unreachable dead code
(`computer_env.perform`, MCP gateway, type-level composer, autonomous CoW, mechanism/grid, typed GUI
labels). Tests naming those tiers were not exercising that controller path. This change deletes the
dead block instead of pretending it is live capability.

## 3. What changed

`canonical/swe_kernel/closed_loop_autonomous_controller_v1.py`:

1. Added `_record_gap_and_read_knowledge()`, the read-only half of learn-on-failure:
   - records a learnable front-door gap in the ignorance ledger when memory writes are allowed;
   - reads JIT knowledge when tier-2 learning, JIT network, and memory writes are allowed;
   - names candidate executables as evidence only;
   - does **not** run a named program, even `--help`;
   - does **not** acquire/register a capability or retry the goal.
2. Rewrote the documentation-fallback refusal site:
   - preserves the precise front status when nothing ran and the gap was recorded;
   - moves the carrier decision to `carrier_gate` instead of deleting it;
   - reports `executed=False`, `side_effects_may_exist=False` only when no prior execution/uncertain
     effects are present;
   - keeps prior execution or uncertain effects visible rather than erasing them.
3. Replaced the old effectful tail (`--help` subprocess, acquisition, registration, retry) with the
   same read-only helper. No execution authority is granted.
4. Honors `READ_ONLY`/`OFF`: no persisted-gap claim and no JIT source-value credit when memory writes
   are forbidden.

After, on the same audio/pdf goals:

```text
solve_or_learn() -> FAIL__RAW_GOAL_COMPILATION_GAP
                    executed=False
                    side_effects_may_exist=False
                    carrier_gate.status=FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT
                    refusal_precedes_the_carrier_gate=True
                    documentation_fallback_executed=False
                    learning.gap_recorded=True
                    learning.gap_id=<stable sha256-based id>
                    learning.what_to_learn_next=[...]
                    learning.knowledge.status=PASS__JIT_KNOWLEDGE_RESOLVED
                    learning.knowledge.kinds_answered includes >=2 kinds
                    learning.attempted=False
```

This is a real seam repair. It is **not** a new capability, not a benchmark gain, and not permission
to execute the effectful half.

## 4. What is real on this tree

- **Precise refusal preservation.** The carrier gate no longer eats the compile gap when nothing ran.
- **Ignorance ledger intake.** A real gap can be recorded and ranked again from the live controller.
- **JIT knowledge retrieval.** The live path can fetch external public evidence from multiple kinds
  of sources. External documents remain K1 evidence; they grant no authority.
- **Admission harm is measurable.** The existing lesson-admission instrument reproduced:
  - ungated lesson with no victims: `crystallized=True`, `UNGATED`, 0 held-out programs executed,
    `inclusive_cap` broken;
  - gated: `ADMISSION_REJECT:BROKE_CORRECT_PROGRAM:inclusive_cap`;
  - safe suite: `ADMIT`.
- **Confinement substrate exists but is not admitted at the door.** `confinement_v1` measured 9/9 in
  its own suite, but no general door consults it as an admitted effect carrier.
- **Weight training is not ready.** Weight-space fuel: 258 units / 64 verified against threshold 5000,
  `ready_to_train=False`. Training-readiness census: 5 stores / 71 rows / 0 ready.
- **The honest suite is not green.** The live orientation brief still reports the honest baseline:
  11,525 cases, 11,166 passed, 344 failed, 1 collection error, 14 skipped. This PR does not rewrite
  that baseline.

## 5. What is not real

- No “learn once, permanently correct everywhere” result.
- No general computer-use execution authority.
- No admitted confinement carrier wired into the front door.
- No weight update, no GPU training run, no sentience result.
- No independent-personnel verification of this repair.
- No global completeness of opportunity data. “All hidden data” is not a finite retrieval target;
  the honest mechanism is bounded search, explicit uncertainty, and falsification.
- No capability credit from dead code, document titles, retrieved packages, or non-firing rules.
- No claim that the three remaining failures below are fixed.

## 6. Single bottleneck

The best current lever is **cheap, strong, environment-specific verification plus safe admission of
what is learned**.

Reason:

1. The admission gate already shows that ungated permanence can store a harmful lesson.
2. The repaired seam shows that without a precise gap signal, the system cannot even target the
   right verification work.
3. The effectful half still waits on an admitted confinement/effect-adoption decision. Wiring more
   learners before that decision would only create more unadmitted or ungated paths.
4. Weight training is downstream of verified, deduplicated, contrastive traces. The current fuel and
   readiness measurements say the dataset is not there yet.

So the order is:

```text
precise gap -> bounded knowledge -> candidate hypothesis -> held-out verification + regression budget
-> admitted persistence -> only then effectful execution under admitted confinement
-> only then weight consolidation from admitted traces
```

## 7. Ranked next work

1. **Wire the existing admission gate into one autonomous caller at a time.**
   Start with the caller that can supply real victim programs with their own specs. Require
   `ADMIT` before persistence; keep `UNGATED` visible as a refusal to claim learned capability.
   Do not let callers declare their own falsification families.

2. **Get the owner’s confinement/effect-adoption decision.**
   The pre-registered seam doc names the only semantically complete design: run in disposable
   confinement, verify declared effects, then adopt only declared bytes through write authority and
   preimage rollback. An agent must not grant itself that authority.

3. **Repair the base64 misroute and missing `pypdf` dependency honestly.**
   `use base64 to encode text into out.txt` currently routes to `pdf.extract.text.pypdf` and raises
   `PYPDF_IMPORT_FAILED`. That is a real routing/dependency defect, not a reason to weaken the
   boundary or fake an attempt.

4. **Correct stale test premises only with new evidence.**
   Two failures expect refusal where tier0a semantic generalization now answers correctly. Update
   the premise to a still-impossible goal or assert the safe answered behavior, but do not relax
   safety assertions.

5. **Collect admitted, contrastive, deduplicated traces before any weight work.**
   Keep no-retrieval probes and archive-regression probes. Train only from admitted evidence, not
   from every success.

6. **Independent verification.**
   A verifier who did not write this change must reproduce the seam tests and the admission-harm
   measurement before any progress claim beyond “producer-run repair.”

## 8. Killed before implementation

- Training on all successful traces now.
- Growing memory/skill libraries without admission.
- Counting a non-firing rule as safety.
- Letting callers label their own falsification cases.
- Running a named program’s `--help` as “knowledge.”
- Treating retrieved documents as owned capability.
- Relaxing the 50 ms wake-sleep assertion to make a run green.
- Re-deriving already-measured numbers instead of reusing the instruments.
- Breadth-of-environments as a substitute for a verified admission mechanism.

## 9. Test ledger — real counts, including failures

Producer-run on this tree with `.venv/bin/python -m pytest`:

```text
Baseline affected front suites:
  5 failed, 72 passed, 7 subtests passed in 44.74s

Final admission/JIT/seam set:
  canonical/tests/test_learn_on_failure_carrier_seam_v1.py
  canonical/tests/test_jit_knowledge_v1.py
  canonical/tests/test_lesson_admission_gate_v1.py
  canonical/tests/test_lesson_admission_regression_v1.py
  canonical/tests/test_weight_space_fuel_v1.py
  canonical/tests/test_experience_corpus_training_readiness_v1.py
  -> 98 passed in 55.48s

Final carrier/guard set, excluding the timing-sensitive wake suite:
  canonical/tests/test_learn_on_failure_carrier_seam_v1.py
  canonical/tests/test_the_carrier_gate_does_not_eat_the_reason_v1.py
  canonical/tests/test_a_precise_refusal_is_not_replaced_by_a_generic_one_v1.py
  canonical/tests/test_compiled_cli_confinement_guard_v1.py
  canonical/tests/test_python_ast_query_transfer_v1.py
  -> 45 passed, 2 subtests passed in 2.18s

Wake/sleep suite alone:
  canonical/tests/test_wake_sleep_recall_and_specialist_controller_v1.py
  -> 6 passed in 7.27s

Known remaining failures, isolated:
  test_integrated_autonomous_loop_v1.py::...gap_ledger_gui_fallback_and_honest_refusal
  test_computer_unconfined_route_guard_v1.py::...unconfined_query_or_archive
    subtest goal='count lines in notes.txt'
  test_live_route_memory_consult_v1.py::LearnOnFailureTests::test_a_goal_naming_a_real_program_is_attempted
  -> 3 failed, 1 passed, 1 subtests passed in 8.72s
```

Timing flake observed and not hidden: when the wake/sleep suite was run together with the carrier
set under load, `test_tier0_compiled_http_skill_recall_stays_under_50ms_across_even_wake_episodes`
failed once with wall time about 3.8–4.8 s against the 50 ms assertion. Alone it passed. No assertion
was relaxed.

Other checks:

```text
python3 execution_guard/repo_integrity_guard_v1.py --self-test -> PASS
python3 execution_guard/repo_integrity_guard_v1.py             -> PASS, 17 rules, 0 violations
python3 execution_guard/agent_orientation_check_v1.py verify   -> ok:true
.venv/bin/python -m compileall                                 -> clean
git diff --check                                               -> clean
```

The three remaining failures are pre-existing and out of this PR’s narrow scope:

- two stale refusal premises where tier0a now answers safely and correctly;
- one base64 misroute to `pdf.extract.text.pypdf` plus missing `pypdf`.

They are reported, not papered over.

## 10. External context used for ranking, not authority

These sources informed the ranking. They are not Brain capability evidence and do not verify this
repair:

- FGSE, arXiv:2611.14326 — falsification-gated self-evolution; harmful committed updates still 3.6%.
- GRASP, arXiv:2605.29668 — ablation localizes gain to the acceptance gate, not skill writing.
- OSWorld 2.0, arXiv:2606.29537 — long-horizon computer use remains weak; verification skipping and
  state drift are central failure modes.
- ASCENT, arXiv:2610.05303; Experience Distillation, arXiv:2607.21051; ENGRAM, arXiv:2611.09472 —
  weight/memory consolidation needs verifier-accepted data and release gates.
- Continual-ARC, arXiv:2611.14505; SkillLearnBench, arXiv:2604.20087; CL-Bench, arXiv:2606.05661 —
  more exposure/memory does not reliably produce unseen-task capability.

## 11. Stop condition

Stop here: the read-only seam is repaired and tested; the effectful half remains refused; no
capability or terminal credit is claimed. The next admissible work is admission-gate wiring,
owner-authorized confinement/effect adoption, and independent reproduction — not a broader learner
built on top of an unadmitted carrier.

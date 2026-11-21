# Authorized answer intake: one bit, no model, no guess

**2026-11-21 · branch `arena/4e192cf3-brain` · authority `NONE__PRODUCER_RUN_SANDBOX`.**
Receipt: `intake/RECEIPT_AUTHORIZED_ANSWER_INTAKE_20261121_V1.json`.
Tool: `intake/authorized_answer_intake_v1.py`. Tests: 11 passed.
Targeted regression: 88 passed. No capability, acceptance, benchmark, or terminal credit.

---

## 0. Requirements restated before acting

The mission is our own weights, architecture and agent for arbitrary computer use and
software engineering, learning from one experience, with **zero runtime model calls**,
no parameter warehouse of world facts, and an external inspectable/editable/deletable
instant-knowledge store. Every step must research the project and the frontier first,
remove before adding, pick the single bottleneck, kill bad designs, build the minimal
strongest thing, test on the hardest honest cases, report verified/unverified/failed
separately, and never claim completion before §6 is met. One branch, one merge.

The §2 contradiction is resolved as before and is unchanged by this round: forbidden
is a parameter lookup of memorized facts and a runtime dependency on another model;
allowed is a computed mechanism plus an external store of authored facts and learned
slots that can be added, removed, and re-verified. An answer written by the task's
author is external knowledge. The mechanism that binds it to an executable check is
computed code and carries no parameter.

## 1. Research findings

### This project (non-obvious names included)

The tree already contains, and this round reused rather than rebuilt:

- `canonical/runtime/osworld_verified_task_ledger_v1.py` — compiles only explicit
  paths and quoted facts, and gates `DONE` on fresh guest PASS receipts; refuses a
  pathless or relation-unresolved instruction with a named error.
- `canonical/runtime/osworld_sensor_request_bridge_v1.py` — admits a computed
  directory sensor and re-measures it on a fresh filesystem.
- `canonical/runtime/osworld_v21_host_guest_ops_v1.py` and `osworld_v21_state_ops_v1.py`
  — the pinned state-op compiler and real guest executor.
- `canonical/runtime/osworld_v21_receipt_dataflow_v1`–`v3`, `workflow_policy_v1–v13`,
  `unified_policy_v10–v17`, `recovery_policy_v1/v2`, `osworld_verified_policy_v1` —
  receipt resolution, subgoal compilation and the existing zero-model runtime stack.
- `canonical/swe_kernel/lesson_admission_gate_v1.py` and
  `verified_skill_crystallizer_v1.py` — already gate persistence on held-out
  execution and equivalence-under-precondition. `admission_corpus_audit_v1.py` audits
  how many stored rows actually earned that right.
- `canonical/tools/agreement_is_not_equivalence_v1.py` — shows a residual is closed
  by a proof or a witness, not by more agreeing runs; it names the proof/tool boundary.
- `canonical/tools/breadth_buys_what_repetition_cannot_v1.py` — measures that breadth
  shrinks a goal's class and then saturates, leaving a residual priced in words.
- `canonical/tools/the_assertion_is_the_demand_v1.py`,
  `the_goal_is_a_discriminator_v1.py`, `the_goal_is_a_relation_over_the_run_v1.py`,
  `the_vocabulary_is_the_artifact_v1.py` — the recognition, active-question and
  relation-vocabulary instruments that precede any synthesis.
- `canonical/swe_kernel/pins_from_the_reverted_part_v1.py` and
  `reach_the_changed_site_v1.py` — pin synthesis and directed input generation;
  0 of 8 then 2 of 8 on the same class of real fixes.
- `the_smallest_question_that_makes_this_checkable_v1.py`,
  `the_engine_on_forty_five_unseen_fixes_20261123_V1` — in 134 real one-line fixes,
  one verified repair, and it was one the engine had already solved. The published
  next step was to elicit content, not to buy more oracle.

Nothing in the tree accepts a task author's answer as a typed, provenance-bound
completion condition and compiles it into a guest assertion. That was the gap.

### Frontier (inputs only; never runtime dependencies)

The hardest computer-use benchmark remains OSWorld 2.0: 108 long-horizon workflows,
best reported binary completion 20.6%, and the authors' own diagnosis is that agents
lose hidden state, drop constraints, guess instead of asking, and spend under 7% of
their budget detecting and repairing errors [1](https://osworld-v2.xlang.ai/)
[7](https://arxiv.org/pdf/2606.29537v1). On coding, SWE-bench Pro is the live hard
target and its own verifier has been audited at roughly 8.5% false accepts and 24%
false rejects [1](https://codingfleet.com/blog/swe-bench-pro-explained-the-new-standard-for-ai-coding-benchmarks-2026/).
The frontier's answer to underspecification is to ask the user — EMNLP 2026's
uncertainty-aware scaffold reports 69.40% resolve rate by clarifying, but it uses
frontier models as the asker and the judge [5](https://aclanthology.org/2026.findings-emnlp.15/).
Continual-learning benchmarks reach the same boundary from another direction:
SkillLearnBench finds that self-feedback drifts without external grounding, and
stored skills still lag human-authored ones [3](https://arxiv.org/pdf/2604.20087).

Those results are evidence for the architecture, not capability we may borrow. No
frontier model, paper artifact, or benchmark answer is a runtime dependency here.

## 2. Verdict on the core hypothesis

**True:** one executed experience can be retained exactly in an external store and
replayed against fresh state; a mechanical check can make a rule permanent without
training; a verifier outside the producer is the part that makes the store safe.

**False:** "experience the most advanced action once, therefore own the capability."
A trace records what happened, not what the goal meant; a finite agreement is not
equivalence; a one-line action cannot encode the relation it served. This tree's 134
real fixes and 1 verified repair, and OSWorld 2.0's 20.6%, are direct measurements.

**Unproven:** arbitrary computer use, natural-language understanding, sentience,
single-experience identification of an arbitrary new goal.

**The real bottleneck:** when the instruction does not bind a machine-checkable
slot, the system has no content to verify. More actions, more repetitions, a larger
store and a better search all multiply a missing term. The missing term is authored
intent. The only lawful source is the instruction's author, and the only lawful form
is an explicit answer that can be compiled into a check.

Why cannot we simply "let the model experience the most advanced coding actions
once"? Because the answer is not an action list. The same `.encode()` action serves
different demands in different frames; the store would have to hold either a
world-fact lookup (forbidden) or a model call to interpret the new frame (forbidden).
What can be stored lawfully is a relation plus its check, or a typed answer supplied
by the author and verified by execution.

## 3. The single plan, and what was killed

**Plan:** ask exactly one question when — and only when — the existing ledger names
an unbindable slot; accept only a typed, provenance-bound answer from an authorized
author; compile it into an existing guest assertion; re-measure on fresh state; write
the answer to an external deletable store; never overwrite an explicit instruction;
never let an answer alone mean success.

| route | verdict | reason |
|---|---|---|
| DELETE | rejected | the ledger and guest verifier are load-bearing |
| BYPASS | rejected | it is exactly the unverified-DONE defect |
| REUSE | accepted | ledger compiler, pinned state ops and admitted sensor already exist |
| ADAPT | accepted | augment the ledger's requirements, not its kernel |
| SUBSTITUTE | killed | a model NLU or judge is forbidden at runtime |
| COMPOSE | accepted | question → typed answer → assertion → receipt → store |
| SYNTHESIZE_NEW_PRIMITIVE | rejected | no new primitive is needed; the missing part is an intake |

Killed ideas: a general natural-language parser (would need world knowledge),
a learned answer ranker (unidentified parameters), scoring plausible answers by
test count (the "533 greens, 0 of 12 preserved" failure), asking before the world
has been exhausted (the project's `log₂(class)` rule), and accepting free prose as
an executable fact (unfalsifiable).

## 4. What was built

`intake/authorized_answer_intake_v1.py` adds:

- `missing_slots(state)` — reads the ledger's own refusal reasons (plus explicitly
  declared slots) and returns zero or more questions. It never infers intent from
  wording.
- `compiled_requirements(state)` — validates author, instruction digest, slot and
  type; turns one `PATH` answer into the existing `DIRECTORY_SENSOR` requirement and
  one `VALUE` answer into an existing `TEXT_CONTAINS` requirement; refuses conflicts,
  stale digests, untrusted authors, prose without a typed value, and overrides of
  explicit instruction facts.
- `decide(state, base)` — gates a base policy's `DONE`. If requirements are all
  fresh-verified, a stalled base may finish; otherwise the base never gets a
  free `DONE` and receives exactly one `ASK_USER` action.
- `persist_answers` / `load_answers` — an external JSON store with author and
  instruction digest; deleting the file is the whole unlearning operation.

`intake/osworld_intake_policy_v1.py` is a root-level candidate composition with the
existing `osworld_verified_policy_v1`; no byte-pinned kernel was edited. It is not
wired into the live runtime by this round, and that is a stated limit.

## 5. Tests and honest results

`intake/tests/test_authorized_answer_intake_v1.py` — **11 passed**:

- an under-specified instruction asks one question and never finishes;
- a natural-language sentence containing one absolute path yields a real
  `ASSERT_SENSOR_REQUEST` executed by a fresh guest subprocess and then `DONE`;
- a typed value answer yields `ASSERT_TEXT_CONTAINS` on a real file and then `DONE`;
- untrusted author, conflicting answers, a digest from a different instruction,
  untyped prose, and overriding an explicit path are all refused;
- a real later `DELETE` invalidates an older directory PASS;
- one persisted answer is reloaded and deletion restores the question.

Targeted regression: `test_osworld_verified_task_ledger_v1.py`,
`test_osworld_v21_state_ops_v1.py`, `test_guest_state_ops_execute_for_real_v1.py`,
`test_osworld_sensor_request_bridge_v1.py`, plus the new suite — **88 passed**.
The first run had 2 failures caused by `PIL` absent from the fresh venv, not by a
code change; after installing Pillow in the build venv all 88 passed. This is
disclosed rather than hidden.

Receipt `intake/RECEIPT_AUTHORIZED_ANSWER_INTAKE_20261121_V1.json` records the exact
pytest command, output, source hashes, criteria and zeros. Authority: NONE.
Producer-run sandbox. No benchmark was run, no model was called, no parameter was
stored, and no money was spent.

## 6. What is not claimed, and the next bottleneck

Not claimed: natural-language understanding, a full OSWorld 2.1 run, GUI or browser
success, transfer to an unseen coding repository, a benchmark score, independent
verification, a registered capability, or §6 completion. The adapter is root-level
and not yet the live runtime entry point. `truth.achieved` stays `false`.

**Next bottleneck:** wire this intake into the live verified OSWorld policy and run
it on untouched tasks with genuinely underspecified instructions; then widen the
typed answer set from `PATH`/`VALUE` to relations over product-native receipts
without turning the answer grammar into a new world-knowledge warehouse. Falsifier:
a task that reaches `DONE` on a slot no authorized source supplied, or an answer that
survives deletion of its store.

# One purpose gate: ask only on a real contrast

**2026-11-21 · branch `arena/67c67d7e-brain` · receipt `intake/RECEIPT_PURPOSE_GATE_20261121_V1.json` · authority NONE**

---

## 0. Requirements restated

Own model, architecture and agent; zero runtime model calls; no knowledge house in parameters; every
parameter computed and justified; knowledge only in an external, inspectable, deletable store; one
experience must suffice in unseen environments; hardest open computer-use and software-engineering
tests; no borrowed outputs, leakage or hand-solving; no questions to the owner; research first, kill
bad ideas, build the ultimate minimal whole, test honestly, loop until §6, never claim done early.
§2 is resolved as: external typed knowledge/skills are allowed, weights hold computed mechanisms,
and knowledge must be addable/removable without retraining. `truth.achieved` stays `false`.

## 1. Research findings

**Project (non-obvious names):** `THE_GOAL_IS_A_RELATION_OVER_THE_RUN_20261127_V1.md` measured 323
action sequences collapsing to 136 traces, 9 final states reached by oppositely judged runs, an
*empty* final-state grammar (0 survivors), and a run grammar with 5–6 questions, 0 false accepts and
1 leave-one-out false reject. It names the frontier bottleneck: **reachable contrast set at the
frontier** — identification is cheap, making the run is not. `THE_DEMAND_IS_A_RELATION_20261125_V1.md`
recovers 2/75 real one-line repairs, both `if x:` → `if x is not None:`, and rejects an
argument-projection false accept. `A_DEMAND_MUST_BE_BOUND_TO_THE_SITE_20261122_V1.md` binds a demand
only when an assertion operand holds what the site produced. `THE_REPERTOIRE_IS_A_QUERY_20261129_V1.md`
finds 437 programs and 4,621 options re-derived in 47 s, 0 of 80 accepted options mutating state, and
no threshold separating serveable from unserveable needs. `intake/authorized_answer_intake_v1.py`
already compiles one typed authorized answer into a guest assertion; no runtime wiring was added here.

**Frontier:** OSWorld 2.0's strongest reported setting reaches 20.6% binary / 54.8% partial on 108
long workflows [5](https://arxiv.org/pdf/2606.29537v1). DeepSWE's audit reports SWE-bench Pro
verifier false-accept 8.5% and false-reject 24.0%, versus 0.3%/1.1% for its own functional verifiers
[4](https://arxiv.org/pdf/2607.07946). ReviveBench found 28 verifier defects, including two false
positives, while auditing hidden verifiers [1](https://arxiv.org/html/2609.36161v1). ExecCritic keeps
one fail-to-pass test hidden and gives the repair agent only bounded execution feedback
[2](https://arxiv.org/html/2609.09133v1). These are inputs, not capability claims for us.

## 2. §3 verdict

- **Real:** a demonstrated action's state transition replays exactly; identification from run-level
  relations is sound and cheap; a typed answer from the instruction's author can be compiled into a
  check without a model.
- **False:** that an action is the unit of learning, that a final state carries the goal, that a
  class of minimal statements is a class of intentions, or that "keep the repertoire forever" is the
  right form of a machine's action vocabulary.
- **Unproven:** that a general natural-language instruction can be compiled to a checkable purpose
  without an authorized typed answer; that any of this transfers to GUI/browser computer use here.
- **Missing:** live agent wiring, a reachable contrast producer for real repositories, and any run
  on OSWorld 2.0 / SWE-bench Pro under our own zero-model system.

Why not "experience the most advanced coding actions once"? The trace records what an action did, not
which relation the failing run violated. Without a run that exhibits the difference, more experience
is the same observation. A model call cannot manufacture that contrast, and a parameter holding the
answer would be an unfalsifiable lookup. The blocker is purpose plus reachable contrast, not speed.

## 3. Single plan and killed ideas

**Plan:** one gate in front of the answer intake: compile candidate statements to predicates; evaluate
them on real runs from an environment not used to fit them; ask only if a run separates them; accept
only a typed selection from an authorized author with matching instruction digest and question
fingerprint; store it externally; delete to unlearn; never emit `DONE`.

| route | verdict | reason |
|---|---|---|
| DELETE | rejected | ledger, trace tools and answer intake are load-bearing |
| BYPASS | rejected | would let an answer create success without a check |
| REUSE | accepted | existing trace tools, authorized intake, real machine builders |
| ADAPT | accepted | one gate, no canonical kernel edit |
| SUBSTITUTE | killed | model NLU, learned ranker, plausibility score: forbidden or unfalsifiable |
| COMPOSE | accepted | contrast → question → typed answer → external store → existing ledgers |
| SYNTHESIZE_NEW_PRIMITIVE | rejected | no new runtime primitive is justified |

Killed: asking between equivalent statement names; accepting free prose as a check; allowing an
untrusted author or stale digest to select a candidate; storing a candidate in parameters.

## 4. Build and hard evidence

`intake/residual_question_gate_v1.py` asks only when a real contrast separates candidates.
`intake/bulk_copy_environment_v1.py` is a real CLI machine whose one action adds two copies.
`intake/purpose_gate_v1.py` composes the gate with the already-built authorized-answer intake,
validates typed selections and persists them externally.

Receipt `intake/RECEIPT_PURPOSE_GATE_20261121_V1.json`, all criteria declared before execution:

| criterion | result |
|---|---|
| P1 no zero-information question | GIT: **18 real runs, 0 distinguishing, `NO_QUESTION`** |
| P2 real contrast pays it | BULK_COPY: **1 real run, 1 distinguishing**, goal mismatches `{1, 0}` |
| P3 refusals | untrusted, stale digest, wrong kind, invented candidate all refused |
| P4 external store | accepted selection reloads; deletion restores `ASK_USER` |
| P5 zeros | 0 model calls, 0 parameters, 0 network calls; 19 real runs |

Cost 0.8 s, authority `NONE__PRODUCER_RUN_SANDBOX`. No benchmark score and no independent
verification are claimed. The "goal" judge is the project's own deterministic predicate, not a new
human judgment, and no actual user answered.

## 5. Tests

`intake/tests/test_purpose_gate_v1.py` — **3 passed**: zero-information residual cannot be asked;
real contrast asks, identifies the zero-mismatch statement, refuses four bad answer forms and accepts
only a typed authorized selection; external store reloads and deletion restores the question.
The earlier authorized-answer suite remains **11 passed**; combined **14 passed**.

## 6. Non-claims and next bottleneck

Not claimed: full OSWorld/SWE-bench performance, GUI or browser success, natural-language
understanding, live runtime wiring, registered capability, independent verification, or §6 completion.
`truth.achieved` remains `false`.

**Next bottleneck:** the reachable contrast set on real repositories. The gate can now refuse a fake
question, but it cannot manufacture a run that a real repository's checker can judge. The next
falsifier is a held-out repository where an edit is selected by one executed demonstration and
survives the project's own test suite; the measured baseline to beat is 2/75 real one-line repairs,
and a count of plausible edits is not evidence.

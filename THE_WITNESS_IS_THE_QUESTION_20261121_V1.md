# The witness is the question — and one bit is not enough

*2026-11-21 · branch `arena/8634d5e2-brain` · receipt `canonical/verification/THE_WITNESS_IS_THE_QUESTION_20261121_V1.json` · tool `canonical/tools/the_witness_is_the_question_v1.py` · 11 tests · 0 parameters · 0 model calls*

Authority: **NONE**. Producer-run measurement on this machine. Nothing here changes `truth.achieved`.

---

## 0. Requirements restated, and the §2 contradiction resolved

The binding constraints are: no runtime model call; no knowledge warehouse in weights; every retained parameter derived and justified; knowledge acquired just in time; learning writes to an external, inspectable, editable store; the agent must learn from one experience in new environments; no question to the owner during this work; research project then web; build the minimal ultimate mechanism and test it on the hardest material available, reporting failures verbatim.

**§2 resolved as before, and confirmed by this round's implementation:** the user's sentence lives in a JSON store (the receipt and the statement strings), the computed mechanism lives in code, and no weight stores a world fact. Adding or removing a sentence requires no retraining. The apparent contradiction — "instant learning permanently" vs "zero knowledge house" — is not a contradiction once persistence is a store and parameters are only mechanisms. If evidence had shown a better boundary, this round would have recorded it; it did not.

## 1. What already existed in the project

Searched the repo (17,918 tracked files; 630 markdown, 5,993 python, 10,440 JSON), the live pointer, the terminal authority, `AGENTS.md`, the orientation brief, and the newest dated rounds. Non-obvious names that mattered:

- `canonical/tools/breadth_buys_what_repetition_cannot_v1.py` — one grammar, 244 terms, 29,890 hypotheses, **555 executed runs** over TARBALL / FILESYSTEM / SQLITE. Result: 622 behaviours; the goal's minimal class shrinks **4 → 2 → 2** and stops. Its §9 pre-registers exactly this round: *build the intake and price it; falsify if a chosen sentence mispredicts a fourth environment.*
- `canonical/tools/the_goal_is_a_relation_over_the_run_v1.py` — the run-term grammar (`created_once`, `monotone`, `final:count[...]`) and `_increased_once`, the project's own statement of "copy it once and keep it".
- `canonical/tools/the_goal_is_a_quotient_of_the_trace_v1.py` — `portable_judge`, the portable reading of that sentence; witnesses for cheaper projections.
- `canonical/tools/the_assertion_is_the_demand_v1.py` and `the_space_is_the_artifact_v1.py` — recognition before search; hypothesis grammar with one production while real fixes use four.
- `instant_learning_demo.py`, `closed_loop_autonomous_controller_v1.py`, `VERIFIED_SKILLS_BUNDLE_V1.json` — one demonstration does become a reusable rule; retracted claims around it are noted in `YOU_WERE_RIGHT_ALL_ALONG.md`, `FINAL_SOLUTION_SUMMARY.md`, `COMPLETE_SOLUTION_SUMMARY.md`.
- `execution_guard/repo_integrity_guard_v1.py` and `AGENTS.md` — terminal truth is not editable data; verification needs a different verifier; no self-promotion.

Earlier "both problems completely solved" documents are retracted in-tree and were treated as history, not evidence.

## 2. What the frontier says (searched 2026-11-21, treated as input, not truth)

- Multi-hunk repair is the measured hard case: 220 of 500 SWE-bench Verified instances are multi-hunk; repair accuracy falls with hunk divergence and spatial dispersion across four agent families [1](https://arxiv.org/html/2511.11012) [2](https://arxiv.org/pdf/2511.11012). This independently matches the project's "hypothesis grammar has one production, fixes use four" finding.
- Structural characterisation of multi-hunk patches and their effect on repair success [3](https://arxiv.org/html/2506.04418v2).
- The 2026 survey of agentic issue resolution places SWE-Bench Pro (1,865 tasks, 41 repos, four languages) as the current long-horizon coding bar [4](https://dl.acm.org/doi/10.1145/3849702).
- Computer use: OSWorld 2.0 reset a saturated benchmark to ~20.6% for the best system at release, then to ~77.9% within ten weeks; OSWorld-Verified tops now exceed the ~72% human baseline, and results are scaffold-sensitive [5](https://o-mega.ai/articles/the-2025-2026-guide-to-ai-computer-use-benchmarks-and-top-ai-agents) [6](https://arxiv.org/html/2605.20530v1). A feasibility gate that refuses impossible tasks is a measured part of the best published OSWorld scaffold [7](https://www.pointer.ai/blog/sota) — the same "recognition before search" law this project found from the other end.
- EMNLP 2026 work grounds instructions as *regular languages over environment event traces* (CEDAR) and reports that prompting alone neither decides when to ask nor produces disambiguating questions [8](https://aclanthology.org/volumes/2026.emnlp-main/). That is the nearest external cousin of this round: the object to be pinned is a relation over a run, and the missing bit is in language. None of it was used at runtime; no model was called.

## 3. Verdict on the core hypothesis

| Claim | Verdict | Evidence |
|---|---|---|
| One verified experience yields a reusable, durable rule | **True, narrow** | In-tree one-demonstration receipts; the rule survives a fresh process. |
| One experience in a new arbitrary environment identifies the goal permanently | **False as stated** | 555 runs over three machines leave a 2-sentence class; this round adds a fourth machine where the language-selected sentence accepts 4/8 runs the user rejects. |
| Breadth of environments helps | **True but saturating** | 4 → 2 → 2; the third machine removed zero sentences. A *different kind* of machine still bought new counterexamples. |
| The residual is exactly `log2(class)` user bits | **False once reach changes** | Over the fitted machines, one bit closes the class. On an unseen machine, repairs cost 9 more user bits (1 accepted situation + 4 counterexample situations + 4 re-checks; 10 total). |
| The missing bit is language, not a bigger learner | **True** | Every repair here was a user bit on a rendered situation; no search, no weight, no replay could supply it. |
| Sentience follows from the mechanism | **Unproven** | No experiment here measures it. Claiming otherwise would repeat the retracted pattern. |

**Real bottlenecks, in order:** (1) a finite set of environments under-approximates the behaviours that can falsify a sentence; (2) the number of user bits is `H(goal | reach of the environments)`, not `log2(class over fitted runs)`; (3) the repair assumes the goal is a conjunction of grounded terms — a goal outside the 244-term grammar is refused, not fitted. Not a bottleneck: replay volume, store size, weights.

## 4. The single plan, with rejected ideas

**Build a computed language intake that treats the difference between surviving sentences as a question, then lets unseen environments falsify the answer and repair it from more user bits.**

1. Read the two-sentence residual from the executed 555-run receipt.
2. Enumerate short hypothetical count histories; keep one on which the class splits; render it as a situation, not a hypothesis name; ask one bit; select the consistent sentence.
3. Execute a fourth real machine the selection never saw; measure agreement with the user's verdict.
4. For every accepted-by-sentence / rejected-by-user situation, ask the user; conjoin a grounded term that the user accepted elsewhere and rejects here. Fail closed when no such term exists.
5. Execute a fifth machine used by nothing before its own evaluation; measure the repaired sentence there.

**Rejected, with reasons:**

- *Ask the user to choose between the two printed sentences.* That is a leading question in the project's own vocabulary and exposes the hypotheses; the witness must be a situation the user can judge without knowing the grammar.
- *Train a small model to parse the user's words.* Runtime model call; also a knowledge house. Forbidden by §0 and unnecessary: the question is computed from the truth table.
- *Pick the sentence with more fitted support, or the shorter one.* Both are preference, not evidence; they would have picked `monotone ∧ final==1`, which is *worse* on the fourth machine (6/8 vs 4/8 for the other one — both wrong, and frequency gives no signal).
- *Re-run more traces of the same three machines.* The 12-01 measurement already showed saturation; the new information came from a different reach, not more repetitions.
- *Fit a term to the held-out labels directly.* That is leakage and hand-solving. Every term added here is confirmed by a user bit on a rendered situation; no machine label enters the repair function.
- *Declare the one-bit sentence "the answer" after the fifth check.* The fifth machine shows all three candidates at 1.0; it confirms but does not discriminate. The discriminating evidence is the fourth machine's failure, which is recorded.

## 5. Build and measured results

Files: `canonical/tools/the_witness_is_the_question_v1.py`, `canonical/tests/test_the_witness_is_the_question_v1.py`, `canonical/verification/THE_WITNESS_IS_THE_QUESTION_20261121_V1.json`, this document.

The computed question is:

> Situation: at the start there is one copy of the new content. step 1: nothing changes, so 1 copy remains. Is the goal already achieved in this situation?

One `false` bit selects `created_once[probe_new_content]`. Its one-bit price is real **for the fitted closure** (C3). Then:

| stage | machine | runs | result |
|---|---|---|---|
| selection | hypothetical situations (not runs) | — | 2 sentences → 1, 1 question |
| falsifier | PRELOADED_FILESYSTEM, real filesystem + real atoms | 8 (0 positive) | chosen accepts 4 it should reject; rejected alternative accepts 2. **C4 MET** |
| repair | user bits on rendered situations | 10 bits total | `created_once[…] ∧ final:count[…]==1`, 8/8 on the falsifier |
| fifth check | TWO_ATOM_FILESYSTEM, unseen repertoire | 14 (6 positive) | repaired 14/14; chosen and rejected also 14/14 — confirmation without discrimination |

All eight declared criteria C1–C8 are MET in the receipt; 11/11 dedicated tests pass. Refusals are pinned: an equivalent class returns `NO_SEPARATING_WITNESS`, a non-boolean answer returns `INVALID_ANSWER`. Zero model calls, zero stored parameters, zero network calls at run time. Total tool wall time 0.2 s (the upstream 555-run receipt is an input, not re-executed).

**Adversarial after-check, not part of the receipt:** the repaired sentence was also run against a sixth, unused machine (GIT's own commit-log reader): 17 executed runs, 8 user-positive; both the one-bit sentence and the repaired sentence agreed on 17/17. This confirms but again does not discriminate. A first attempt at this probe failed because the scratch root directory did not exist, so the machine's reader emitted no rows; that harness error is recorded here rather than reported as a capability result.

## 6. What is not claimed

- The user in the receipt is scripted: its bits come from the project's `portable_judge`, the in-repo encoding of "copy it once and keep it". A human would supply the same bits; the intake never sees the judge or any machine label during selection or repair.
- Hypothetical situations are **not** runs and are never counted as runs. Only the fourth and fifth machines are executed.
- The repaired sentence is a conjunction inside this 244-term grammar. It agreeing with the judge on the fifth machine is partly tautological — the terms came from the same vocabulary the judge is written in. The new information is the *cost* of getting there after falsification, not a benchmark score.
- No edit is composed, no SWE-bench instance is solved, no GUI is driven. This prices the sentence an edit would be for. The 2026 hard bars in §2 remain unmeasured for our system.

## 7. Next bottleneck, pre-registered

**Environment reach, not the learner.** The one-bit question was generated from hypothetical count histories; the repair had to ask about real situations from a new machine. The next round must (i) generate witness situations from *executed runs of a machine whose reach was not used to build the grammar*, (ii) measure how many user bits are needed when the goal is not a conjunction of grounded terms, and (iii) only then compose an edit against a live codebase and test it on untouched SWE-bench Pro / OSWorld 2.0 instances with the project's own suite as the verifier. Pre-registered falsifiers: a repaired conjunction that fails on a sixth environment; a goal for which the intake returns `NO_REPAIRING_TERM` while the user can still state it; or any user bit that the system could have obtained from a run it had already executed.

Reproduction:

```
python3 canonical/tools/the_witness_is_the_question_v1.py \
  --receipt canonical/verification/THE_WITNESS_IS_THE_QUESTION_20261121_V1.json --depth 2
python3 -m pytest canonical/tests/test_the_witness_is_the_question_v1.py -q   # 11 passed
```

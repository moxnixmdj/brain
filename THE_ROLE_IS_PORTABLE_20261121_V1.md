# The role is portable

*2026-11-21 · branch `arena/8634d5e2-brain` · receipt `canonical/verification/THE_ROLE_IS_PORTABLE_20261121_V1.json` · tool `canonical/tools/the_role_is_portable_v1.py` · 7 new tests, 26 total in the three-round chain · 0 parameters · 0 model calls*

Authority: **NONE**. Producer-run measurement. `truth.achieved` untouched.

---

## 0. Requirements restated

Own model, zero runtime model calls, no memorised fact warehouse, derived parameters only, knowledge in an inspectable store, one experience in a new environment must become permanent, no questions to the owner, project then web research, first principles, minimal ultimate design, hard honest tests without leakage, loop until §6. §2 is again confirmed: the learned sentence is a string in a JSON receipt; the code computes with it and stores no fact in a parameter.

## 1. The failure this round fixes

Last round learned, from 68 executed filesystem runs,

```
monotone[probe_seed_content] ∧ ¬final:has[seed]=probe_seed_content
```

for the project's `moved_judge` ("the original was moved, not copied and deleted"). It scored 128/128 on deeper runs of the **same** filesystem. On a git reader it cannot even be evaluated: `seed` is a filename there and a commit hash here. Both of its two representations on the source pool contained a private identity. Correct, but unportable.

## 2. Project research

- `the_goal_is_a_relation_over_the_run_v1.py`: run-term vocabulary and the real goal judges.
- `the_goal_is_a_quotient_of_the_trace_v1.py`: `_holders_by_step`, `_content_to_identities`, `_identity_histories` and `moved_judge` — the existing evidence that holder identity, not content multiset, carries the moved goal.
- `the_vocabulary_is_the_artifact_v1.py`: CARD/MULTISET/ORDER/IDENT/PAIRING and the measured fact that the vocabulary decides what a learner can say.
- `instant_learning_in_a_new_environment_v1.py`: `effect_of` computes surface-neutral roles (ARG/OLD/PROBE) from two readings, never from a name.
- `the_question_is_a_real_run_v1.py`: membership questions, two-literal literal spaces, and the measured rule that identification after a query budget is not correctness. This round **reuses its learner unchanged** and only supplies a different vocabulary; it also extends `learn` with an optional forced-counterexample map, which is the one new line of mechanism.

## 3. Frontier research (input, not truth)

RoleWorld (Oct 2026) uses reusable functional-role prototypes instead of environment-specific objects and transfers world models without parameter updates [1](https://arxiv.org/abs/2610.13172). Relational structural causal models show that parameter sharing alone does not identify behaviour across unseen relational skeletons [2](https://arxiv.org/html/2606.14892v1). Object-centric work reports systematic generalization only when representations are built over objects and their interactions rather than surface slots [3](https://arxiv.org/html/2511.02225v1). This round is the smallest computed instance of that principle: a role is a function of the machine's own reading, not a name in it. Benchmark bars (SWE-bench Pro ~61.5%, OSWorld 2.0 ~20.6% binary) remain untouched by our system [4](https://personalagentbench.com/benchmarks/swe-bench/) [5](https://decodethefuture.org/en/ai-agent-benchmarks-2026/).

## 4. §3 verdict, updated

- **True:** a goal can be learned from user bits on executed runs; a positive-conjunction class cannot express all real goals; negation fixes that within one tool.
- **Newly measured true:** correct-but-unportable is a distinct failure mode from wrong. Removing identity terms and adding one computed role transfers both goals to a machine with different private names, **without changing the learner or the bit price**.
- **False:** that "same reader shape" implies "same inference". A term can be evaluable on two machines and still encode a name that exists on only one.
- **Unproven:** transfer across different tool families (git/tarball/sqlite), edit composition, frontier benchmarks, sentience.

## 5. Single plan, rejected ideas, build

**Plan:** compute the set of private identities from the source traces; keep only grounded terms whose text does not mention one; add `holders_changed[c]` computed from start/end holder sets; run the existing learner on those literals; verify on a second real filesystem whose seed is named `origin`; show the old sentence is ungrounded there.

**Rejected:**
- *Retrain or add weights for renaming.* Forbidden and unnecessary; a rename is a change of vocabulary, not of mechanism.
- *Rewrite the learner.* It already identifies a behaviour from user bits; the defect was what it was allowed to say. One optional forced-counterexample argument was added after the learner's own audit proved identification ≠ correctness.
- *Translate names with a lookup table.* That is a memorised map, not a computed role, and would fail for a machine whose holders are hashes.
- *Drop identity terms and hope.* Without `holders_changed`, no two-literal representation of the moved goal exists on the source pool; the check is in the receipt (E2).
- *Hand-pick the second machine's goal positives.* Both machines are reset by their own code and judged by the project's own judges; no label was supplied by hand.

## 6. Results

| | source filesystem | renamed filesystem |
|---|---|---|
| seed identity | `seed` | `origin` |
| executed runs | 68 | 68 |
| portable | 26 positive; `created_once[probe_new_content]` | 68/68 |
| moved | 11 positive; `¬two_copies[probe_seed_content] ∧ holders_changed[probe_seed_content]` | 68/68 |
| old identity sentence | correct on source | `UNGROUNDED_ON_SECOND_MACHINE` |

The role vocabulary has 32 terms, zero private-identity terms and one computed holder-change role per content. Both goals identified within their bit budgets (16 bits total). All six declared criteria E1–E6 are MET. 7 new tests pass; 26 tests pass across all three rounds of this chain. Guard: 17 rules, 0 violations. Zero model calls, zero stored parameters, zero network calls at run time.

**Two errors made and fixed in this round, recorded:** (i) the first receipt run chose `at_least_once ∧ ¬at_least_once` because the source machine had not been reset before its arguments were read, leaving the moved goal with no positives; (ii) the learner's bit budget can end on a sentence consistent with asked runs, so a user-verified pool audit with forced counterexamples was added to the vocabulary round. Neither was edited out of the history.

**Adversarial cross-tool probe (not part of the receipt).** The role sentence *does* evaluate on 19 git runs and 11 tarball runs, where the old identity sentence could not be evaluated at all; it agrees on 19/19 and 11/11. But the moved goal has **zero** positive runs on both, so those numbers confirm grounding only, not discrimination. This is why the receipt's transfer test uses the renamed filesystem, where the goal has 11 positives.

**Honest limits.** Both receipt machines are real filesystems with different private names. The vocabulary supplies one role generator; a goal needing another role is refused. No edit, GUI, SWE-bench or OSWorld task is attempted.

## 7. Next bottleneck, pre-registered

**Compose the verified sentence with an action.** The system can now learn a goal and recognise it on a renamed tool, but it still does not *reach* the goal: no action is composed from the sentence. Next: use a role-based sentence as the acceptance predicate for a deterministic planning loop over the project's bound capability registry, require the project's own suite to verify the resulting edit, and test on untouched real repair tasks rather than CLI machines. Pre-registered falsifiers: a plan that satisfies the sentence but fails the real suite; a goal whose role representation is ungrounded on a different tool family; or any success that borrows a label from the test set.

Reproduction:

```
python3 canonical/tools/the_role_is_portable_v1.py \
  --receipt canonical/verification/THE_ROLE_IS_PORTABLE_20261121_V1.json --depth 3
python3 -m pytest canonical/tests/test_the_role_is_portable_v1.py -q   # 7 passed
```

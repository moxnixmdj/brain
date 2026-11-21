# Contract-veto repair on real published bugs

**Date:** 2026-11-21 · **Authority:** NONE, producer-run sandbox · **Branch:** `arena/ca510ed5-brain`

## Objective and progress claim

Objective, verbatim: `BUILD_THE_MOST_CAPABLE_GENERAL_RELIABLE_AND_RESOURCE_EFFICIENT_PROBLEM_SOLVING_SYSTEM_POSSIBLE`.

Progress class: `VERIFIED_RELIABILITY_GENERALIZATION_OR_EFFICIENCY_GAIN` in the producer sandbox — two previously unrepaired real bugs are now repaired with one computed edit each, verified on fresh copies by both the corpus's own test and a derived output contract. No independent verifier, capability credit, or terminal claim is made.

## Requirements read before acting

The live orientation brief, `AGENTS.md`, the objective JSON, the orientation contract, the capability-ownership and model-independence laws, the capability-acquisition and true-capability laws, the recursive-obsolescence law, the resource-bounded-bytes law, the white-box harvesting law, and the repository-integrity policy were read this session. Every prompt in this mission was treated as new; the §2 contradiction is resolved as an external, inspectable, editable knowledge store with computed mechanisms in weights, and no runtime model calls.

## Route walk

1. **DELETE** — removed the reader artifact and the language intake for aliases; neither is a capability.
2. **BYPASS** — fourth-machine and mutable-content falsifiers were used only to refuse merges, never as the repair.
3. **REUSE** — reused the existing QuixBugs harness, patch search, repair loop, run grammar and breadth `Analysis`.
4. **ADAPT** — enumerated every tarball member occurrence and deleted inert literals from the goal grammar.
5. **SUBSTITUTE** — a derived output contract substitutes for a hidden answer key; no donor output enters the solver.
6. **COMPOSE (selected)** — composed two structure-derived mutation families with a contract veto over the existing loop.
7. **CONFIGURE** — the new families are off by default and live in a separate module, so the legacy grammar and the historical `REACH_OF_THE_GRAMMAR` receipt stay byte-honest. Only this round's receipt prices the extension.
8. **INTEGRATE / SYNTHESIZE** — not used; no capability was registered and no model or dialogue was added.

## What the frontier and project showed

Active-learning work on temporal specifications (Roy & Huang, arXiv:2611.17866) treats rivals that agree over the feasible trace domain as equivalent and discards them without a query; bounded searches preserve soundness but not completeness. That supported quotienting the run grammar instead of asking the user. The same source's distinction between unconstrained traces and feasible traces under an environment explains why a premise that holds on three machines must be re-measured when a fourth machine can restore a value.

Inside the project, the hard-corpus audits showed the binding/residual problem was not the absence of more tests: the repair search had no grammar entry for a midpoint index or a recursive argument order, and published tests alone had already certified a `find_in_sorted` patch that recurses forever on an unseen array.

## What was built and measured

| Round | Receipt | Result |
|---|---|---|
| Reader fidelity | `canonical/verification/TAR_READER_ARTIFACT_20261121_V1.json` | 175 concatenated-literal artifact classes → 0; ambiguous classes 265 → 147; goal class 2 → 1; F1–F5 MET |
| Inert literal deletion | `canonical/verification/FINITE_TRACE_INVARIANTS_20261121_V1.json` | computed constant-count premise on all three machines; ambiguous classes 147 → 137; mutable-content falsifier separates the pair; I1–I5 MET |
| Contract-veto repair | `canonical/verification/CONTRACT_VETO_REPAIR_20261121_V1.json` | two real QuixBugs repairs; S1–S5 MET |

### Contract-veto repair

- `gcd`: `gcd(a % b, b)` → `gcd(b, a % b)`, found in **14** candidates, one accepted edit.
- `find_in_sorted`: `binsearch(mid, end)` → `binsearch(mid + 1, end)`, found in **52** candidates, one accepted edit.
- On fresh copies, the corpus's byte-identical test and the generated output contract both returned `rc=0`.
- Control: the previously measured published-only patch passed all published cases (`rc=0`) but failed the derived contract (`rc=1`; 56 failed, 400 passed). It recurses forever on `[1, 3]` with `x=2`.
- The contract tests assert the task's own stated output relation. They contain no expected patch, no answer-key value and no hidden label.
- Cost: 25.2 s, 0 model calls, 0 stored parameters, 0 network calls at run time.

All five criteria were declared in `canonical/tools/contract_veto_repair_v1.py` before the receipt run and reported as MET. Four unit tests pass in `canonical/tests/test_contract_veto_repair_v1.py`.

## Honest limits and what is still open

- This is one producer-run sandbox. No independent identity re-ran the receipt; no capability was registered; `truth.achieved` remains false.
- Only two contract forms are implemented, selected by the task's own output sentence. A task outside those forms is refused rather than guessed.
- Passing a finite contract grid is evidence, not a proof of total correctness.
- No GUI, browser, OSWorld 2.0, Terminal-Bench 4.0 or SWE-bench Pro task was run in this round. §6 remains open.
- `EXT_JQ_TABLE` remains an unbindable near-miss. The goal-compilation benchmark still reports 21/23 compiled and 19/23 expected capability selected.
- Several pre-existing repository tests fail under the locally restored pytest 9 environment. The same failures reproduce on the untouched base; they are not claimed fixed here.

## Next test, not a stopping point

Run the same structural-and-contract route across every previously unrepaired QuixBugs task, then on an unseen computer-use environment where one experience must bind the contract. Keep the record of refusals: a task without a derived contract must fail closed, not pass on published cases alone.
